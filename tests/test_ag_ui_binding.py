# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the ACAP AG-UI binding (Governance over AG-UI)."""

from __future__ import annotations

import pytest

from acap.ag_ui import (
    GOVERNANCE_KEY,
    adherence_escalation_interrupt,
    adherence_event_custom,
    consent_interrupt,
    policy_state_snapshot,
    resolve_adherence_escalation,
    resolve_consent,
)
from acap.types.adherence_event import AdherenceDecision, AdherenceEvent
from acap.types.consent_record import ConsentDecision, ParsedClaim
from acap.types.policy_document import ACAP_EXTENSION_URI

HASH = "sha256:9f2c0011"


def _claims() -> list[ParsedClaim]:
    return [ParsedClaim(claim_id="c1", understood=True, disputed=False)]


def _consent_it(tool_call_id=None):
    ev = consent_interrupt(
        policy_version="1.2.0",
        policy_hash=HASH,
        summary="Allow sharing pharmacy records with the pricing agent?",
        tool_call_id=tool_call_id,
    )
    return ev["outcome"]["interrupts"][0]


def _escalation_it():
    ev = adherence_escalation_interrupt(
        consent_record_id="rec-1",
        action="aggregate_sessions",
        claim_id="c4",
        clause_evaluated="§3.4.2",
        reasoning="Action matches prohibition §3.4.2; ambiguous scope.",
    )
    return ev["outcome"]["interrupts"][0]


# --- policy state snapshot (B-5) ---------------------------------------------

def test_policy_snapshot_keyed_by_acap_uri():
    ev = policy_state_snapshot(
        policy_version="1.2.0", policy_hash=HASH, policy_document={"claims": []})
    assert ev["type"] == "STATE_SNAPSHOT"
    assert ACAP_EXTENSION_URI in ev["snapshot"]
    assert ev["snapshot"][ACAP_EXTENSION_URI]["policy_hash"] == HASH


# --- consent interrupt construction ------------------------------------------

def test_consent_interrupt_default_is_confirmation():
    it = _consent_it()
    assert it["reason"] == "confirmation"
    assert "toolCallId" not in it
    gov = it["metadata"][GOVERNANCE_KEY]
    assert gov["uri"] == ACAP_EXTENSION_URI           # B-1
    assert gov["type"] == "ConsentRecord"
    assert gov["policy_hash"] == HASH


def test_consent_interrupt_bound_to_tool_call():
    it = _consent_it(tool_call_id="tc-9")
    assert it["reason"] == "tool_call"
    assert it["toolCallId"] == "tc-9"


# --- consent resolution (B-3 typed resume) -----------------------------------

def test_resolve_consent_accepted():
    it = _consent_it()
    rec = resolve_consent(
        interrupt=it,
        resume={"interruptId": it["id"], "status": "resolved",
                "payload": {"decision": "accepted", "policy_hash": HASH}},
        record_id="rec-1", caller_agent_id="did:caller", callee_agent_id="did:callee",
        parsed_claims=_claims(), accepted_at="2026-04-01T10:00:00Z",
    )
    assert rec.decision is ConsentDecision.ACCEPTED
    assert rec.policy_hash == HASH
    assert rec.policy_version == "1.2.0"


def test_resolve_consent_rejection_is_in_payload():
    it = _consent_it()
    rec = resolve_consent(
        interrupt=it,
        resume={"interruptId": it["id"], "status": "resolved",
                "payload": {"decision": "rejected", "policy_hash": HASH}},
        record_id="rec-1", caller_agent_id="did:caller", callee_agent_id="did:callee",
        parsed_claims=_claims(), accepted_at="2026-04-01T10:00:00Z",
    )
    assert rec.decision is ConsentDecision.REJECTED


def test_resolve_consent_cancelled_fails_closed_to_rejected():
    it = _consent_it()
    rec = resolve_consent(
        interrupt=it, resume={"interruptId": it["id"], "status": "cancelled"},
        record_id="rec-1", caller_agent_id="did:caller", callee_agent_id="did:callee",
        parsed_claims=_claims(), accepted_at="2026-04-01T10:00:00Z",
    )
    assert rec.decision is ConsentDecision.REJECTED


def test_resolve_consent_rejects_hash_mismatch():
    it = _consent_it()
    with pytest.raises(ValueError):
        resolve_consent(
            interrupt=it,
            resume={"interruptId": it["id"], "status": "resolved",
                    "payload": {"decision": "accepted", "policy_hash": "sha256:dead"}},
            record_id="rec-1", caller_agent_id="did:caller", callee_agent_id="did:callee",
            parsed_claims=_claims(), accepted_at="2026-04-01T10:00:00Z",
        )


def test_resolve_consent_resolved_requires_decision():
    it = _consent_it()
    with pytest.raises(ValueError):
        resolve_consent(
            interrupt=it,
            resume={"interruptId": it["id"], "status": "resolved", "payload": {}},
            record_id="rec-1", caller_agent_id="did:caller", callee_agent_id="did:callee",
            parsed_claims=_claims(), accepted_at="2026-04-01T10:00:00Z",
        )


def test_resolve_consent_rejects_foreign_interrupt():
    foreign = {"id": "x", "reason": "confirmation",
               "metadata": {GOVERNANCE_KEY: {"uri": "https://example.com/other", "type": "ConsentRecord"}}}
    with pytest.raises(ValueError):
        resolve_consent(
            interrupt=foreign,
            resume={"interruptId": "x", "status": "resolved",
                    "payload": {"decision": "accepted", "policy_hash": HASH}},
            record_id="r", caller_agent_id="a", callee_agent_id="b",
            parsed_claims=_claims(), accepted_at="2026-04-01T10:00:00Z",
        )


# --- adherence: custom stream + escalation -----------------------------------

def test_adherence_event_custom_annotation():
    ev = adherence_event_custom(AdherenceEvent(
        event_id="e1", consent_record_id="rec-1", action="search_catalog",
        clause_evaluated="§2.1", claim_id="c1", decision=AdherenceDecision.PERMIT,
        reasoning="Permitted under §2.1.", timestamp="2026-04-01T10:01:00Z"))
    assert ev["type"] == "CUSTOM"
    assert ev["name"] == ACAP_EXTENSION_URI
    assert ev["value"]["decision"] == "permit"


def test_escalation_interrupt_shape():
    it = _escalation_it()
    assert it["reason"] == "confirmation"
    gov = it["metadata"][GOVERNANCE_KEY]
    assert gov["uri"] == ACAP_EXTENSION_URI
    assert gov["type"] == "AdherenceEvent"
    assert gov["clause_evaluated"] == "§3.4.2"


def test_resolve_escalation_permit():
    it = _escalation_it()
    ev = resolve_adherence_escalation(
        interrupt=it,
        resume={"interruptId": it["id"], "status": "resolved",
                "payload": {"decision": "permit", "reasoning": "Principal approved."}},
        event_id="e9", timestamp="2026-04-01T10:02:00Z")
    assert isinstance(ev, AdherenceEvent)
    assert ev.decision is AdherenceDecision.PERMIT
    assert ev.reasoning == "Principal approved."
    assert ev.clause_evaluated == "§3.4.2"


def test_resolve_escalation_cancelled_fails_closed_to_deny():
    it = _escalation_it()
    ev = resolve_adherence_escalation(
        interrupt=it, resume={"interruptId": it["id"], "status": "cancelled"},
        event_id="e9", timestamp="2026-04-01T10:02:00Z")
    assert ev.decision is AdherenceDecision.DENY
