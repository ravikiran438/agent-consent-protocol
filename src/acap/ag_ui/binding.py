# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AG-UI binding for ACAP (Agent Consent and Adherence Protocol).

AG-UI (the Agent-User Interaction protocol) is the agent <-> human-app
transport, alongside A2A (agent <-> agent) and MCP (agent <-> tools). Consent is
a human decision, so AG-UI is ACAP's natural transport. This module carries
ACAP's two human-in-the-loop moments over AG-UI under the cross-cutting
"Governance over AG-UI" convention:

  * **Consent gate.** The ``PolicyDocument`` is published as a
    ``STATE_SNAPSHOT`` keyed by ``ACAP_EXTENSION_URI`` (B-5: resume-required
    state before the gate); the decision is solicited with an **interrupt**
    (``reason: "confirmation"``, or ``"tool_call"`` when bound to a specific
    consequential action). The principal's resume payload becomes a typed
    ``ConsentRecord`` -- a rejection is ``decision: "rejected"`` *in the
    payload* (B-3), never an AG-UI ``cancelled``.
  * **Per-action adherence.** Routine ``AdherenceEvent``s stream as ``CUSTOM``
    events so proof-of-adherence stays in the transcript. When a claim is
    ambiguous or disputed the runtime decision is ``escalate`` -- that is the
    one place adherence needs a human, so it renders as a ``confirmation``
    interrupt whose resume becomes a typed ``AdherenceEvent``.

The binding is dependency-free: it builds plain JSON-serializable AG-UI event
dicts. Identity travels in ``metadata.governance.uri`` so a governance-aware
client routes the interrupt while a generic AG-UI client falls back to
``message`` + ``responseSchema`` and still works (B-2, non-breaking).
"""

from __future__ import annotations

from typing import Any, Optional

from acap.types.adherence_event import AdherenceDecision, AdherenceEvent
from acap.types.consent_record import ConsentDecision, ConsentRecord, ParsedClaim
from acap.types.policy_document import ACAP_EXTENSION_URI

# Key under an interrupt's ``metadata`` / a Custom event that carries identity.
GOVERNANCE_KEY = "governance"

# Resume payload for a consent interrupt. A rejection is encoded as
# ``decision: "rejected"`` here (B-3) -- never as AG-UI ``status: "cancelled"``.
CONSENT_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["accepted", "rejected", "conditional"],
            "description": "The principal's decision on the presented policy.",
        },
        "policy_hash": {
            "type": "string",
            "description": "SHA-256 of the PolicyDocument the principal saw; "
            "must match the hash bound into the interrupt.",
        },
    },
    "required": ["decision", "policy_hash"],
    "additionalProperties": False,
}

# Resume payload for an adherence escalation interrupt.
ADHERENCE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["permit", "deny"],
            "description": "The principal's ruling on the escalated action.",
        },
        "reasoning": {
            "type": "string",
            "description": "Optional principal-supplied justification.",
        },
    },
    "required": ["decision"],
    "additionalProperties": False,
}


# --- consent gate ------------------------------------------------------------

def policy_state_snapshot(
    *, policy_version: str, policy_hash: str, policy_document: dict[str, Any]
) -> dict[str, Any]:
    """AG-UI ``STATE_SNAPSHOT`` publishing the PolicyDocument under review.

    Emit before the consent interrupt (B-5) so the frontend can render the
    full policy and a resume can rebuild context from the same hash.
    """
    return {
        "type": "STATE_SNAPSHOT",
        "snapshot": {
            ACAP_EXTENSION_URI: {
                "type": "PolicyDocument",
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "document": policy_document,
            }
        },
    }


def consent_interrupt(
    *,
    policy_version: str,
    policy_hash: str,
    summary: str,
    tool_call_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a ``RUN_FINISHED`` interrupt soliciting a consent decision.

    ``summary`` is a plain-language description of what is being consented to.
    Binding the interrupt to a specific consequential action is expressed by
    passing ``tool_call_id`` (``reason`` becomes ``"tool_call"``); otherwise the
    gate is a standalone ``"confirmation"``. The ``policy_hash`` is carried in
    ``metadata.governance`` so the resumed ``ConsentRecord`` is tamper-evidently
    bound to the exact policy the principal saw.
    """
    interrupt: dict[str, Any] = {
        "id": f"acap-consent-{policy_hash}",
        "reason": "tool_call" if tool_call_id else "confirmation",
        "message": summary,
        "responseSchema": CONSENT_RESPONSE_SCHEMA,
        "metadata": {
            GOVERNANCE_KEY: {
                "uri": ACAP_EXTENSION_URI,
                "type": "ConsentRecord",
                "policy_version": policy_version,
                "policy_hash": policy_hash,
            }
        },
    }
    if tool_call_id:
        interrupt["toolCallId"] = tool_call_id
    return {
        "type": "RUN_FINISHED",
        "outcome": {"type": "interrupt", "interrupts": [interrupt]},
    }


def resolve_consent(
    *,
    interrupt: dict[str, Any],
    resume: dict[str, Any],
    record_id: str,
    caller_agent_id: str,
    callee_agent_id: str,
    parsed_claims: list[ParsedClaim],
    accepted_at: str,
    valid_until: str = "on_version_bump",
    prev_record_id: Optional[str] = None,
    principal_id: Optional[str] = None,
) -> ConsentRecord:
    """Turn an AG-UI resume into a typed, validated ``ConsentRecord``.

    The orchestrator supplies the structural context (the agent pair, the
    parsed-claim interpretation, chain linkage); the human supplies only the
    ``decision``. A ``status: "cancelled"`` (abandoned) resume is recorded as
    ``REJECTED`` -- absence of an affirmative decision is not consent
    (fail-closed). The ``policy_hash`` echoed in the payload must match the one
    bound into the interrupt (B-1). Raises ``ValueError`` if the interrupt is
    not an ACAP consent gate, or (B-4) if a resolved resume carries no decision.
    """
    gov = (interrupt.get("metadata") or {}).get(GOVERNANCE_KEY) or {}
    if gov.get("uri") != ACAP_EXTENSION_URI or gov.get("type") != "ConsentRecord":
        raise ValueError("interrupt is not an ACAP consent gate")

    status = resume.get("status")
    payload = resume.get("payload") or {}

    if status == "cancelled":
        decision = ConsentDecision.REJECTED
    elif status == "resolved":
        if "decision" not in payload:
            raise ValueError("resolved consent resume carries no decision (B-4)")
        decision = ConsentDecision(payload["decision"])
        echoed = payload.get("policy_hash")
        if echoed is not None and echoed != gov["policy_hash"]:
            raise ValueError("resume policy_hash does not match the presented policy")
    else:
        raise ValueError(f"unknown resume status {status!r}")

    return ConsentRecord(
        record_id=record_id,
        prev_record_id=prev_record_id,
        caller_agent_id=caller_agent_id,
        callee_agent_id=callee_agent_id,
        policy_version=gov["policy_version"],
        policy_hash=gov["policy_hash"],
        parsed_claims=list(parsed_claims),
        decision=decision,
        accepted_at=accepted_at,
        valid_until=valid_until,
        principal_id=principal_id,
    )


# --- per-action adherence ----------------------------------------------------

def adherence_event_custom(event: AdherenceEvent) -> dict[str, Any]:
    """Render a routine ``AdherenceEvent`` as a ``CUSTOM`` annotation.

    Streams the per-action proof-of-adherence reasoning into the AG-UI
    transcript (non-blocking) so the human sees which clause governed each
    action and why.
    """
    return {
        "type": "CUSTOM",
        "name": ACAP_EXTENSION_URI,
        "value": {"type": "AdherenceEvent", **event.model_dump()},
    }


def adherence_escalation_interrupt(
    *,
    consent_record_id: str,
    action: str,
    claim_id: str,
    clause_evaluated: str,
    reasoning: str,
) -> dict[str, Any]:
    """Build a ``confirmation`` interrupt for an ``escalate`` adherence decision.

    Used when a claim is ambiguous or disputed (``AdherenceDecision.ESCALATE``):
    the agent halts and asks the principal to rule permit/deny on the specific
    action. The resume becomes a typed ``AdherenceEvent`` via
    ``resolve_adherence_escalation``.
    """
    interrupt = {
        "id": f"acap-adherence-{consent_record_id}-{claim_id}",
        "reason": "confirmation",
        "message": reasoning,
        "responseSchema": ADHERENCE_RESPONSE_SCHEMA,
        "metadata": {
            GOVERNANCE_KEY: {
                "uri": ACAP_EXTENSION_URI,
                "type": "AdherenceEvent",
                "consent_record_id": consent_record_id,
                "action": action,
                "claim_id": claim_id,
                "clause_evaluated": clause_evaluated,
            }
        },
    }
    return {
        "type": "RUN_FINISHED",
        "outcome": {"type": "interrupt", "interrupts": [interrupt]},
    }


def resolve_adherence_escalation(
    *,
    interrupt: dict[str, Any],
    resume: dict[str, Any],
    event_id: str,
    timestamp: str,
    prev_event_id: Optional[str] = None,
    context: Optional[dict[str, str]] = None,
) -> AdherenceEvent:
    """Turn the resume of an adherence escalation into a typed ``AdherenceEvent``.

    The principal's ``permit``/``deny`` ruling is recorded with their reasoning.
    A ``cancelled`` (abandoned) resume resolves **fail-closed** to ``deny``.
    Raises ``ValueError`` if the interrupt is not an ACAP adherence escalation.
    """
    gov = (interrupt.get("metadata") or {}).get(GOVERNANCE_KEY) or {}
    if gov.get("uri") != ACAP_EXTENSION_URI or gov.get("type") != "AdherenceEvent":
        raise ValueError("interrupt is not an ACAP adherence escalation")

    status = resume.get("status")
    payload = resume.get("payload") or {}

    if status == "cancelled":
        decision = AdherenceDecision.DENY
        reasoning = "Escalation abandoned by principal; fail-closed to deny."
    elif status == "resolved":
        if "decision" not in payload:
            raise ValueError("resolved adherence resume carries no decision (B-4)")
        decision = AdherenceDecision(payload["decision"])
        reasoning = payload.get("reasoning") or f"Principal ruled {decision.value} on escalation."
    else:
        raise ValueError(f"unknown resume status {status!r}")

    return AdherenceEvent(
        event_id=event_id,
        prev_event_id=prev_event_id,
        consent_record_id=gov["consent_record_id"],
        action=gov["action"],
        clause_evaluated=gov["clause_evaluated"],
        claim_id=gov["claim_id"],
        decision=decision,
        reasoning=reasoning,
        timestamp=timestamp,
        context=context or {},
    )
