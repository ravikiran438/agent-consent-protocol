# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool registrations for the ACAP MCP server.

Each tool is a thin translation layer: it takes a JSON payload, hands
it to the appropriate ACAP function, and returns a JSON-serializable
result. Pydantic models handle input validation; ACAP's own validators
handle semantic checks. Error messages propagate verbatim so that an
MCP client sees the same diagnostic an in-process caller would.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from acap.extensions.audit_projection import (
    AuditReport,
    AuditReportRequest,
    generate_report,
    validate_audit_report,
)
from acap.extensions.category_preferences import (
    CategoryPreference,
    DataCategory,
    UsageDimension,
    resolve_sensitivity,
)
from acap.extensions.governance_tiering import classify
from acap.extensions.regulatory_context import RegulatoryContext, compute_floor
from acap.types import (
    AdherenceEvent,
    ConsentRecord,
    PolicyDocument,
    UsagePolicyRef,
)
from acap.validators import (
    ChainValidationError,
    TrailValidationError,
    compute_policy_hash,
    validate_adherence_trail,
    validate_consent_chain,
)


# ─────────────────────────────────────────────────────────────────────────────
# Tool schemas
# ─────────────────────────────────────────────────────────────────────────────

# Each tool declares its JSON schema inline so the server exposes it to the
# MCP client. Schemas are tight: required fields are listed, and the inner
# object shapes point at the normative proto definitions by name rather than
# duplicating every field inline.
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "validate_consent_chain": {
        "description": (
            "Validate a consent chain (list of ConsentRecord objects, "
            "oldest-first). Checks prev_record_id linkage, caller/callee "
            "consistency, per-claim coverage, and policy-hash match when "
            "policies are supplied. Raises on first failure."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "chain": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Oldest-first list of ConsentRecord objects.",
                },
                "policy_by_version": {
                    "type": "object",
                    "additionalProperties": {"type": "object"},
                    "description": "Optional map of policy version → PolicyDocument.",
                },
            },
            "required": ["chain"],
        },
    },
    "validate_adherence_trail": {
        "description": (
            "Validate an adherence trail (list of AdherenceEvent objects, "
            "oldest-first). Checks prev_event_id linkage, consent anchor, "
            "and conditional gating."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "trail": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Oldest-first list of AdherenceEvent objects.",
                },
                "chain": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Oldest-first list of ConsentRecord objects "
                    "covering this trail.",
                },
            },
            "required": ["trail", "chain"],
        },
    },
    "compute_policy_hash": {
        "description": (
            "Compute the canonical SHA-256 hash for a PolicyDocument. "
            "Returns the hash in the form 'sha256:<hex>'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy": {
                    "type": "object",
                    "description": "PolicyDocument object.",
                },
            },
            "required": ["policy"],
        },
    },
    "classify_policy_bump": {
        "description": (
            "Governance-tiering extension: diff two PolicyDocument versions "
            "and return the escalation tier plus the structured assessment. "
            "Signals considered: new_claim, removed_claim, modified_claim, "
            "rule_type_inversion, constraint_relaxed, escalate_on_deny_added."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "previous_policy": {"type": "object"},
                "current_policy": {"type": "object"},
                "governance_agent_id": {"type": "string"},
            },
            "required": [
                "previous_policy",
                "current_policy",
                "governance_agent_id",
            ],
        },
    },
    "resolve_sensitivity": {
        "description": (
            "Category-preferences extension: return the principal's "
            "sensitivity for a (category, dimension) query, applying "
            "specific-cell-wins-over-default-row semantics and a LOW "
            "fallback on absence of opinion."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "preferences": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of CategoryPreference entries.",
                },
                "category": {
                    "type": "string",
                    "description": "DataCategory value (e.g. 'biometric', 'health').",
                },
                "dimension": {
                    "type": "string",
                    "description": "UsageDimension value (e.g. 'storage', 'access').",
                },
            },
            "required": ["preferences", "category", "dimension"],
        },
    },
    "compute_floor": {
        "description": (
            "Regulatory-context extension: return the strictest applicable "
            "sensitivity for a (category, dimension) query across principal "
            "preferences and all declared regulatory contexts. The floor is "
            "the max over the LOW < MEDIUM < HIGH lattice."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "principal_preferences": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "contexts": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "RegulatoryContext entries from callee and caller.",
                },
                "category": {"type": "string"},
                "dimension": {"type": "string"},
            },
            "required": [
                "principal_preferences",
                "contexts",
                "category",
                "dimension",
            ],
        },
    },
    "generate_audit_report": {
        "description": (
            "Audit-projection extension: walk a consent chain and adherence "
            "trail for a scoped (caller, callee, window, filters) request "
            "and return a structured report with executive summary, "
            "timeline, per-claim and per-version summaries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "request": {
                    "type": "object",
                    "description": "AuditReportRequest scope specification.",
                },
                "consent_chain": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "adherence_trail": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "policies": {
                    "type": "object",
                    "additionalProperties": {"type": "object"},
                    "description": "Optional map of policy version → PolicyDocument.",
                },
            },
            "required": ["request", "consent_chain", "adherence_trail"],
        },
    },
    "validate_audit_report": {
        "description": (
            "Audit-projection extension: verify structural invariants of a "
            "previously generated AuditReport. Checks 1-based consecutive "
            "sequence indexing, chronological timeline, every entry has at "
            "least one back-reference, and per-claim counts match the "
            "timeline."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "report": {"type": "object"},
            },
            "required": ["report"],
        },
    },
    "validate_usage_policy_ref": {
        "description": (
            "Validate a UsagePolicyRef payload (the body of the "
            "AgentCard.capabilities.extensions[] entry whose URI equals "
            "the ACAP extension URI). Verifies the structural shape: "
            "version, document_uri, document_hash format, "
            "effective_date, acceptance_required + acceptance_endpoint "
            "coherence, natural_language_uri presence."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"ref": {"type": "object"}},
            "required": ["ref"],
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Generic MCP glue — portable across sibling protocol repos.
# Keep these four symbols (ToolInvocationError, _parse, _ok, _fail) in sync
# by convention when copying to phala, pratyahara-nerve, or sauvidya-pace.
# ─────────────────────────────────────────────────────────────────────────────


class ToolInvocationError(Exception):
    """Raised when a tool's handler rejects its input or runtime fails."""


def _parse(cls, payload: Any, label: str):
    try:
        return cls.model_validate(payload)
    except ValidationError as exc:
        raise ToolInvocationError(f"invalid {label}: {exc}") from exc


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps({"ok": True, **payload}, default=str, indent=2)


def _fail(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Tool handlers (repo-specific; everything below this line is ACAP-only).
# ─────────────────────────────────────────────────────────────────────────────


def handle_validate_consent_chain(arguments: dict[str, Any]) -> str:
    chain_raw = arguments.get("chain") or []
    policies_raw = arguments.get("policy_by_version") or {}

    chain = [_parse(ConsentRecord, r, f"chain[{i}]") for i, r in enumerate(chain_raw)]
    policies = {
        v: _parse(PolicyDocument, p, f"policy_by_version[{v}]")
        for v, p in policies_raw.items()
    } or None

    try:
        validate_consent_chain(chain, policy_by_version=policies)
    except ChainValidationError as exc:
        return _fail(str(exc))
    return _ok({"records_validated": len(chain)})


def handle_validate_adherence_trail(arguments: dict[str, Any]) -> str:
    trail_raw = arguments.get("trail") or []
    chain_raw = arguments.get("chain") or []

    trail = [_parse(AdherenceEvent, e, f"trail[{i}]") for i, e in enumerate(trail_raw)]
    chain = [_parse(ConsentRecord, r, f"chain[{i}]") for i, r in enumerate(chain_raw)]
    consent_records_by_id = {r.record_id: r for r in chain}

    try:
        validate_adherence_trail(trail, consent_records_by_id)
    except TrailValidationError as exc:
        return _fail(str(exc))
    return _ok({"events_validated": len(trail)})


def handle_compute_policy_hash(arguments: dict[str, Any]) -> str:
    policy = _parse(PolicyDocument, arguments.get("policy"), "policy")
    return _ok({"hash": compute_policy_hash(policy)})


def handle_classify_policy_bump(arguments: dict[str, Any]) -> str:
    prev = _parse(PolicyDocument, arguments.get("previous_policy"), "previous_policy")
    curr = _parse(PolicyDocument, arguments.get("current_policy"), "current_policy")
    agent_id = arguments.get("governance_agent_id")
    if not isinstance(agent_id, str) or not agent_id:
        raise ToolInvocationError("governance_agent_id is required")

    try:
        diff, assessment = classify(prev, curr, governance_agent_id=agent_id)
    except ValueError as exc:
        return _fail(str(exc))
    return _ok(
        {
            "diff": diff.model_dump(mode="json", exclude_none=True),
            "assessment": assessment.model_dump(mode="json", exclude_none=True),
        }
    )


def _parse_category(raw: Any) -> DataCategory:
    if not isinstance(raw, str):
        raise ToolInvocationError("category must be a string")
    try:
        return DataCategory(raw)
    except ValueError as exc:
        valid = ", ".join(c.value for c in DataCategory)
        raise ToolInvocationError(
            f"unknown category {raw!r}; valid values: {valid}"
        ) from exc


def _parse_dimension(raw: Any) -> UsageDimension:
    if not isinstance(raw, str):
        raise ToolInvocationError("dimension must be a string")
    try:
        return UsageDimension(raw)
    except ValueError as exc:
        valid = ", ".join(d.value for d in UsageDimension)
        raise ToolInvocationError(
            f"unknown dimension {raw!r}; valid values: {valid}"
        ) from exc


def handle_resolve_sensitivity(arguments: dict[str, Any]) -> str:
    prefs_raw = arguments.get("preferences") or []
    prefs = [
        _parse(CategoryPreference, p, f"preferences[{i}]")
        for i, p in enumerate(prefs_raw)
    ]
    category = _parse_category(arguments.get("category"))
    dimension = _parse_dimension(arguments.get("dimension"))

    sensitivity = resolve_sensitivity(prefs, category, dimension)
    return _ok({"sensitivity": sensitivity.value})


def handle_compute_floor(arguments: dict[str, Any]) -> str:
    prefs_raw = arguments.get("principal_preferences") or []
    contexts_raw = arguments.get("contexts") or []

    prefs = [
        _parse(CategoryPreference, p, f"principal_preferences[{i}]")
        for i, p in enumerate(prefs_raw)
    ]
    contexts = [
        _parse(RegulatoryContext, c, f"contexts[{i}]")
        for i, c in enumerate(contexts_raw)
    ]
    category = _parse_category(arguments.get("category"))
    dimension = _parse_dimension(arguments.get("dimension"))

    floor = compute_floor(prefs, contexts, category, dimension)
    return _ok({"sensitivity": floor.value})


def handle_generate_audit_report(arguments: dict[str, Any]) -> str:
    request = _parse(AuditReportRequest, arguments.get("request"), "request")
    chain_raw = arguments.get("consent_chain") or []
    trail_raw = arguments.get("adherence_trail") or []
    policies_raw = arguments.get("policies") or {}

    chain = [
        _parse(ConsentRecord, r, f"consent_chain[{i}]")
        for i, r in enumerate(chain_raw)
    ]
    trail = [
        _parse(AdherenceEvent, e, f"adherence_trail[{i}]")
        for i, e in enumerate(trail_raw)
    ]
    policies = {
        v: _parse(PolicyDocument, p, f"policies[{v}]")
        for v, p in policies_raw.items()
    } or None

    report = generate_report(request, chain, trail, policies)
    return _ok({"report": report.model_dump(mode="json", exclude_none=True)})


def handle_validate_audit_report(arguments: dict[str, Any]) -> str:
    report = _parse(AuditReport, arguments.get("report"), "report")
    try:
        validate_audit_report(report)
    except ValueError as exc:
        return _fail(str(exc))
    return _ok({"timeline_entries": len(report.timeline)})


def handle_validate_usage_policy_ref(arguments: dict[str, Any]) -> str:
    payload = arguments.get("ref")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'ref'")
    ref = _parse(UsagePolicyRef, payload, "ref")

    # document_hash format: "sha256:<64-hex>"
    h = ref.document_hash
    if not (h.startswith("sha256:") and len(h) == len("sha256:") + 64):
        return _fail(
            f"document_hash {h!r} is not a sha256:<64-hex> value"
        )
    try:
        int(h[len("sha256:"):], 16)
    except ValueError:
        return _fail(
            f"document_hash {h!r} hex part is not valid hex"
        )

    # When acceptance_required is true, the acceptance_endpoint MUST be set.
    if ref.acceptance_required and not ref.acceptance_endpoint:
        return _fail(
            "acceptance_required=true requires an acceptance_endpoint"
        )
    return _ok({"ref": "valid"})


HANDLERS: dict[str, Any] = {
    "validate_consent_chain": handle_validate_consent_chain,
    "validate_adherence_trail": handle_validate_adherence_trail,
    "compute_policy_hash": handle_compute_policy_hash,
    "classify_policy_bump": handle_classify_policy_bump,
    "resolve_sensitivity": handle_resolve_sensitivity,
    "compute_floor": handle_compute_floor,
    "generate_audit_report": handle_generate_audit_report,
    "validate_audit_report": handle_validate_audit_report,
    "validate_usage_policy_ref": handle_validate_usage_policy_ref,
}


def list_tool_names() -> list[str]:
    return list(TOOL_SCHEMAS.keys())
