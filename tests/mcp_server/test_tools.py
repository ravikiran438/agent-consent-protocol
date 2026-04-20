# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for the ACAP MCP server tool handlers.

Each handler is tested against JSON-shaped input and output, since that
is the contract exposed to an MCP client. The server wiring (stdio,
asyncio) is not under test here; handlers are called directly.
"""

from __future__ import annotations

import json

import pytest

from acap.mcp_server.tools import (
    HANDLERS,
    TOOL_SCHEMAS,
    ToolInvocationError,
    handle_classify_policy_bump,
    handle_compute_floor,
    handle_compute_policy_hash,
    handle_generate_audit_report,
    handle_resolve_sensitivity,
    handle_validate_adherence_trail,
    handle_validate_audit_report,
    handle_validate_consent_chain,
    list_tool_names,
)


CALLER = "did:agent:caller"
CALLEE = "https://callee.example.com/agent"


def _policy(version: str, claims: list[dict]) -> dict:
    return {
        "version": version,
        "document_uri": f"https://callee.example.com/policy/{version}.json",
        "document_hash": "sha256:" + "0" * 64,
        "effective_date": "2026-03-01T00:00:00Z",
        "claims": claims,
        "publisher": CALLEE,
        "natural_language_uri": "https://callee.example.com/terms",
    }


def _claim(claim_id: str, rule: str = "prohibition") -> dict:
    return {
        "claim_id": claim_id,
        "clause_ref": f"§{claim_id[-1]}",
        "action": "odrl:aggregate",
        "asset": "pii:session_data",
        "rule_type": rule,
        "effective_version": "1.0.0",
    }


def _record(
    record_id: str,
    prev: str | None,
    policy_version: str,
    policy_hash: str,
    claim_ids: list[str],
    accepted_at: str = "2026-03-01T10:00:00Z",
) -> dict:
    return {
        "record_id": record_id,
        "prev_record_id": prev,
        "caller_agent_id": CALLER,
        "callee_agent_id": CALLEE,
        "policy_version": policy_version,
        "policy_hash": policy_hash,
        "parsed_claims": [
            {"claim_id": cid, "understood": True, "disputed": False}
            for cid in claim_ids
        ],
        "decision": "accepted",
        "accepted_at": accepted_at,
        "valid_until": "on_version_bump",
    }


def _event(
    event_id: str,
    prev: str | None,
    consent_record_id: str,
    claim_id: str,
    decision: str,
    timestamp: str = "2026-03-01T10:05:00Z",
) -> dict:
    return {
        "event_id": event_id,
        "prev_event_id": prev,
        "consent_record_id": consent_record_id,
        "action": "odrl:aggregate",
        "clause_evaluated": f"§{claim_id[-1]}",
        "claim_id": claim_id,
        "decision": decision,
        "reasoning": f"test reasoning for {event_id}",
        "timestamp": timestamp,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────────────────────────────────────


def test_schemas_and_handlers_are_consistent():
    schema_names = set(TOOL_SCHEMAS.keys())
    handler_names = set(HANDLERS.keys())
    assert schema_names == handler_names
    assert set(list_tool_names()) == schema_names


def test_every_schema_has_required_fields():
    for name, schema in TOOL_SCHEMAS.items():
        assert "description" in schema, f"{name} missing description"
        assert "inputSchema" in schema, f"{name} missing inputSchema"
        assert schema["inputSchema"]["type"] == "object"


# ─────────────────────────────────────────────────────────────────────────────
# compute_policy_hash
# ─────────────────────────────────────────────────────────────────────────────


def test_compute_policy_hash_returns_sha256_prefix():
    policy = _policy("1.0.0", [_claim("a")])
    result = json.loads(handle_compute_policy_hash({"policy": policy}))
    assert result["ok"] is True
    assert result["hash"].startswith("sha256:")
    assert len(result["hash"]) == len("sha256:") + 64


def test_compute_policy_hash_invalid_input_raises():
    with pytest.raises(ToolInvocationError, match="invalid policy"):
        handle_compute_policy_hash({"policy": {"not": "a policy"}})


# ─────────────────────────────────────────────────────────────────────────────
# validate_consent_chain
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_consent_chain_happy_path():
    policy = _policy("1.0.0", [_claim("a")])
    # Compute the real hash for the chain to match.
    from acap.validators import compute_policy_hash as real_hash
    from acap.types import PolicyDocument

    h = real_hash(PolicyDocument.model_validate(policy))
    chain = [_record("rec-1", None, "1.0.0", h, ["a"])]

    result = json.loads(
        handle_validate_consent_chain(
            {"chain": chain, "policy_by_version": {"1.0.0": {**policy, "document_hash": h}}}
        )
    )
    assert result["ok"] is True
    assert result["records_validated"] == 1


def test_validate_consent_chain_empty_chain_fails():
    result = json.loads(handle_validate_consent_chain({"chain": []}))
    assert result["ok"] is False
    assert "empty" in result["error"]


def test_validate_consent_chain_broken_link_fails():
    h = "sha256:" + "0" * 64
    chain = [
        _record("rec-1", None, "1.0.0", h, ["a"]),
        _record("rec-2", "rec-not-real", "1.0.0", h, ["a"]),
    ]
    result = json.loads(handle_validate_consent_chain({"chain": chain}))
    assert result["ok"] is False
    assert "prev_record_id" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# validate_adherence_trail
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_adherence_trail_happy_path():
    h = "sha256:" + "0" * 64
    chain = [_record("rec-1", None, "1.0.0", h, ["a"])]
    trail = [_event("ev-1", None, "rec-1", "a", "permit")]
    result = json.loads(
        handle_validate_adherence_trail({"trail": trail, "chain": chain})
    )
    assert result["ok"] is True
    assert result["events_validated"] == 1


def test_validate_adherence_trail_unanchored_fails():
    h = "sha256:" + "0" * 64
    chain = [_record("rec-1", None, "1.0.0", h, ["a"])]
    trail = [_event("ev-1", None, "rec-unknown", "a", "permit")]
    result = json.loads(
        handle_validate_adherence_trail({"trail": trail, "chain": chain})
    )
    assert result["ok"] is False


# ─────────────────────────────────────────────────────────────────────────────
# classify_policy_bump (governance-tiering)
# ─────────────────────────────────────────────────────────────────────────────


def test_classify_policy_bump_governance_reviewed_on_new_claim():
    prev = _policy("1.0.0", [_claim("a")])
    curr = _policy("2.0.0", [_claim("a"), _claim("b")])
    result = json.loads(
        handle_classify_policy_bump(
            {
                "previous_policy": prev,
                "current_policy": curr,
                "governance_agent_id": "did:agent:governance",
            }
        )
    )
    assert result["ok"] is True
    assert result["assessment"]["tier"] == "governance_reviewed"


def test_classify_policy_bump_human_required_on_removed_claim():
    prev = _policy("1.0.0", [_claim("a"), _claim("b")])
    curr = _policy("2.0.0", [_claim("a")])
    result = json.loads(
        handle_classify_policy_bump(
            {
                "previous_policy": prev,
                "current_policy": curr,
                "governance_agent_id": "did:agent:governance",
            }
        )
    )
    assert result["ok"] is True
    assert result["assessment"]["tier"] == "human_required"


def test_classify_policy_bump_same_version_returns_error():
    policy = _policy("1.0.0", [_claim("a")])
    result = json.loads(
        handle_classify_policy_bump(
            {
                "previous_policy": policy,
                "current_policy": policy,
                "governance_agent_id": "did:agent:governance",
            }
        )
    )
    assert result["ok"] is False
    assert "share version" in result["error"]


def test_classify_policy_bump_missing_agent_id_raises():
    prev = _policy("1.0.0", [_claim("a")])
    curr = _policy("2.0.0", [_claim("a"), _claim("b")])
    with pytest.raises(
        ToolInvocationError, match="governance_agent_id is required"
    ):
        handle_classify_policy_bump(
            {"previous_policy": prev, "current_policy": curr}
        )


# ─────────────────────────────────────────────────────────────────────────────
# resolve_sensitivity (category-preferences)
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_sensitivity_default_row():
    prefs = [{"category": "biometric", "sensitivity": "high"}]
    result = json.loads(
        handle_resolve_sensitivity(
            {"preferences": prefs, "category": "biometric", "dimension": "storage"}
        )
    )
    assert result["ok"] is True
    assert result["sensitivity"] == "high"


def test_resolve_sensitivity_unknown_category_raises():
    with pytest.raises(ToolInvocationError, match="unknown category"):
        handle_resolve_sensitivity(
            {
                "preferences": [],
                "category": "nonexistent",
                "dimension": "storage",
            }
        )


def test_resolve_sensitivity_unknown_dimension_raises():
    with pytest.raises(ToolInvocationError, match="unknown dimension"):
        handle_resolve_sensitivity(
            {
                "preferences": [],
                "category": "biometric",
                "dimension": "nonexistent",
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# compute_floor (regulatory-context)
# ─────────────────────────────────────────────────────────────────────────────


def test_compute_floor_takes_strictest():
    prefs = [{"category": "health", "sensitivity": "low"}]
    contexts = [
        {
            "framework": "hipaa",
            "role": "covered_entity",
            "obligations": [
                {
                    "obligation_ref": "HYPOTHETICAL-1",
                    "affected_categories": ["health"],
                    "affected_dimensions": ["third_party_sharing"],
                    "minimum_sensitivity": "high",
                    "description": "test",
                }
            ],
        }
    ]
    result = json.loads(
        handle_compute_floor(
            {
                "principal_preferences": prefs,
                "contexts": contexts,
                "category": "health",
                "dimension": "third_party_sharing",
            }
        )
    )
    assert result["ok"] is True
    assert result["sensitivity"] == "high"


# ─────────────────────────────────────────────────────────────────────────────
# generate_audit_report + validate_audit_report (audit-projection)
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_and_validate_audit_report_round_trip():
    from acap.validators import compute_policy_hash as real_hash
    from acap.types import PolicyDocument

    policy_obj = _policy("1.0.0", [_claim("a")])
    h = real_hash(PolicyDocument.model_validate(policy_obj))
    policy_obj["document_hash"] = h

    chain = [_record("rec-1", None, "1.0.0", h, ["a"])]
    trail = [_event("ev-1", None, "rec-1", "a", "permit")]

    gen = json.loads(
        handle_generate_audit_report(
            {
                "request": {
                    "caller_agent_id": CALLER,
                    "callee_agent_id": CALLEE,
                },
                "consent_chain": chain,
                "adherence_trail": trail,
                "policies": {"1.0.0": policy_obj},
            }
        )
    )
    assert gen["ok"] is True
    report = gen["report"]
    # round-trip validation
    v = json.loads(handle_validate_audit_report({"report": report}))
    assert v["ok"] is True
    assert v["timeline_entries"] >= 2  # at least one consent + one event


def test_validate_audit_report_rejects_tampered_timeline():
    from acap.validators import compute_policy_hash as real_hash
    from acap.types import PolicyDocument

    policy_obj = _policy("1.0.0", [_claim("a")])
    h = real_hash(PolicyDocument.model_validate(policy_obj))
    policy_obj["document_hash"] = h

    chain = [_record("rec-1", None, "1.0.0", h, ["a"])]
    trail = [_event("ev-1", None, "rec-1", "a", "permit")]

    gen = json.loads(
        handle_generate_audit_report(
            {
                "request": {
                    "caller_agent_id": CALLER,
                    "callee_agent_id": CALLEE,
                },
                "consent_chain": chain,
                "adherence_trail": trail,
                "policies": {"1.0.0": policy_obj},
            }
        )
    )
    report = gen["report"]
    # tamper: break sequence
    report["timeline"][0]["sequence"] = 999

    v = json.loads(handle_validate_audit_report({"report": report}))
    assert v["ok"] is False
    assert "sequence" in v["error"]
