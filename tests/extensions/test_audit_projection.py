# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for the audit-projection extension.

Covers end-to-end projection of a small consent chain + adherence trail,
filter behavior (time window, version, claim, decision), and the
structural validator.
"""

from __future__ import annotations

import pytest

from acap.extensions.audit_projection import (
    AuditEntryType,
    AuditReportRequest,
    AuditReportValidationError,
    generate_report,
    validate_audit_report,
)
from acap.types import (
    AdherenceDecision,
    AdherenceEvent,
    ConsentDecision,
    ConsentRecord,
    ParsedClaim,
    PolicyClaim,
    PolicyDocument,
    RuleType,
)


CALLER = "did:agent:caller"
CALLEE = "https://callee.example.com/agent"


def _claim(claim_id: str, rule: RuleType = RuleType.PROHIBITION) -> PolicyClaim:
    return PolicyClaim(
        claim_id=claim_id,
        clause_ref=f"§{claim_id[-1]}",
        action="odrl:aggregate",
        asset="pii:session_data",
        rule_type=rule,
        effective_version="1.0.0",
    )


def _policy(version: str, claims: list[PolicyClaim]) -> PolicyDocument:
    return PolicyDocument(
        version=version,
        document_uri=f"https://callee.example.com/policy/{version}.json",
        document_hash=f"sha256:{'0' * 64}",
        effective_date="2026-03-01T00:00:00Z",
        claims=claims,
        publisher=CALLEE,
        natural_language_uri="https://callee.example.com/terms",
    )


def _record(
    record_id: str,
    prev: str | None,
    policy_version: str,
    accepted_at: str,
    claim_ids: list[str],
    decision: ConsentDecision = ConsentDecision.ACCEPTED,
) -> ConsentRecord:
    return ConsentRecord(
        record_id=record_id,
        prev_record_id=prev,
        caller_agent_id=CALLER,
        callee_agent_id=CALLEE,
        policy_version=policy_version,
        policy_hash=f"sha256:{'0' * 64}",
        parsed_claims=[
            ParsedClaim(claim_id=cid, understood=True, disputed=False)
            for cid in claim_ids
        ],
        decision=decision,
        accepted_at=accepted_at,
        valid_until="on_version_bump",
    )


def _event(
    event_id: str,
    prev: str | None,
    consent_record_id: str,
    claim_id: str,
    decision: AdherenceDecision,
    timestamp: str,
) -> AdherenceEvent:
    return AdherenceEvent(
        event_id=event_id,
        prev_event_id=prev,
        consent_record_id=consent_record_id,
        action="odrl:aggregate",
        clause_evaluated=f"§{claim_id[-1]}",
        claim_id=claim_id,
        decision=decision,
        reasoning=f"test reasoning for {event_id}",
        timestamp=timestamp,
    )


# ─────────────────────────────────────────────────────────────────────────────
# generate_report — happy path
# ─────────────────────────────────────────────────────────────────────────────


def _minimal_chain_and_trail():
    records = [
        _record("rec-1", None, "1.0.0", "2026-03-01T10:00:00Z", ["a", "b"]),
        _record("rec-2", "rec-1", "2.0.0", "2026-03-03T10:00:00Z", ["a", "b", "c"]),
    ]
    events = [
        _event("ev-1", None, "rec-1", "a", AdherenceDecision.PERMIT, "2026-03-01T10:05:00Z"),
        _event("ev-2", "ev-1", "rec-1", "b", AdherenceDecision.DENY, "2026-03-02T12:00:00Z"),
        _event("ev-3", None, "rec-2", "c", AdherenceDecision.ESCALATE, "2026-03-04T09:00:00Z"),
        _event("ev-4", "ev-3", "rec-2", "a", AdherenceDecision.PERMIT, "2026-03-04T11:00:00Z"),
    ]
    policies = {
        "1.0.0": _policy("1.0.0", [_claim("a"), _claim("b")]),
        "2.0.0": _policy("2.0.0", [_claim("a"), _claim("b"), _claim("c")]),
    }
    return records, events, policies


def test_generate_report_covers_full_chain():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)

    assert report.caller_agent_id == CALLER
    assert report.callee_agent_id == CALLEE
    # 2 records + 4 events = 6 timeline entries
    assert len(report.timeline) == 6
    # first entry is initial consent
    assert report.timeline[0].entry_type is AuditEntryType.INITIAL_CONSENT
    # subsequent consent is reconsent
    reconsents = [
        e for e in report.timeline
        if e.entry_type is AuditEntryType.RECONSENT_POLICY
    ]
    assert len(reconsents) == 1


def test_generate_report_timeline_is_chronological():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)

    timestamps = [e.timestamp for e in report.timeline]
    assert timestamps == sorted(timestamps)


def test_generate_report_sequences_are_consecutive_from_one():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)

    assert [e.sequence for e in report.timeline] == list(
        range(1, len(report.timeline) + 1)
    )


def test_generate_report_every_entry_has_backreference():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)

    for entry in report.timeline:
        assert entry.consent_record_id or entry.adherence_event_id


def test_generate_report_per_claim_counts_match_events():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)

    by_id = {s.claim_id: s for s in report.claim_summaries}
    # claim 'a': permit x2
    assert by_id["a"].permit_count == 2
    assert by_id["a"].deny_count == 0
    assert by_id["a"].total_evaluations == 2
    # claim 'b': deny x1
    assert by_id["b"].deny_count == 1
    assert by_id["b"].permit_count == 0
    # claim 'c': escalate x1
    assert by_id["c"].escalate_count == 1


def test_generate_report_version_summaries():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)

    by_version = {s.version: s for s in report.version_summaries}
    # v1: 2 events (ev-1 permit, ev-2 deny)
    assert by_version["1.0.0"].total_adherence_events == 2
    # v2: 2 events (ev-3 escalate, ev-4 permit)
    assert by_version["2.0.0"].total_adherence_events == 2
    assert by_version["1.0.0"].claim_count == 2
    assert by_version["2.0.0"].claim_count == 3


def test_generate_report_executive_summary_mentions_counts():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)

    summary = report.executive_summary
    # 2 permits, 1 deny, 1 escalate
    assert "2 were permitted" in summary
    assert "1 denied" in summary
    assert "1 escalated" in summary


# ─────────────────────────────────────────────────────────────────────────────
# filters
# ─────────────────────────────────────────────────────────────────────────────


def test_filter_by_time_window():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(
        caller_agent_id=CALLER,
        callee_agent_id=CALLEE,
        from_timestamp="2026-03-03T00:00:00Z",
        to_timestamp="2026-03-05T00:00:00Z",
    )

    report = generate_report(request, records, events, policies)

    # only rec-2, ev-3, ev-4 in window
    ids = {e.consent_record_id for e in report.timeline if e.consent_record_id}
    ids |= {e.adherence_event_id for e in report.timeline if e.adherence_event_id}
    assert ids == {"rec-2", "ev-3", "ev-4"}


def test_filter_by_policy_version():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(
        caller_agent_id=CALLER,
        callee_agent_id=CALLEE,
        policy_versions=["2.0.0"],
    )

    report = generate_report(request, records, events, policies)

    # v1 records and events are excluded
    for entry in report.timeline:
        assert entry.policy_version == "2.0.0"


def test_filter_by_claim_ids():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(
        caller_agent_id=CALLER,
        callee_agent_id=CALLEE,
        claim_ids=["c"],
    )

    report = generate_report(request, records, events, policies)

    # consent records still appear (they reference all claims); only events
    # for claim 'c' should be in the adherence slots.
    adherence_events = [
        e for e in report.timeline if e.adherence_event_id is not None
    ]
    assert len(adherence_events) == 1
    assert "c" in adherence_events[0].referenced_claim_ids


def test_filter_by_decision():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(
        caller_agent_id=CALLER,
        callee_agent_id=CALLEE,
        decision_filter=[AdherenceDecision.DENY, AdherenceDecision.ESCALATE],
    )

    report = generate_report(request, records, events, policies)

    adherence_types = {
        e.entry_type for e in report.timeline if e.adherence_event_id is not None
    }
    assert AuditEntryType.ADHERENCE_PERMIT not in adherence_types


def test_filter_excludes_other_caller_callee_pairs():
    records, events, policies = _minimal_chain_and_trail()
    # Add a record for a different pair; the projector must ignore it.
    other_record = ConsentRecord(
        record_id="rec-other",
        prev_record_id=None,
        caller_agent_id="did:agent:other-caller",
        callee_agent_id=CALLEE,
        policy_version="1.0.0",
        policy_hash=f"sha256:{'0' * 64}",
        parsed_claims=[
            ParsedClaim(claim_id="a", understood=True, disputed=False)
        ],
        decision=ConsentDecision.ACCEPTED,
        accepted_at="2026-03-01T10:00:00Z",
        valid_until="on_version_bump",
    )
    extended_records = records + [other_record]

    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)
    report = generate_report(request, extended_records, events, policies)

    cross_ref_ids = {e.consent_record_id for e in report.timeline}
    assert "rec-other" not in cross_ref_ids


# ─────────────────────────────────────────────────────────────────────────────
# edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_empty_chain_produces_well_formed_report():
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)
    report = generate_report(request, [], [], None)

    assert report.timeline == []
    assert report.claim_summaries == []
    assert report.version_summaries == []


def test_projector_works_without_policies():
    records, events, _ = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, None)

    # rule_type falls back to 'unknown' without policies
    assert all(s.rule_type == "unknown" for s in report.claim_summaries)


# ─────────────────────────────────────────────────────────────────────────────
# validate_audit_report
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_accepts_generated_report():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)

    report = generate_report(request, records, events, policies)
    validate_audit_report(report)  # no exception


def test_validate_rejects_out_of_order_timeline():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)
    report = generate_report(request, records, events, policies)

    # swap two entries' timestamps to invert chronology
    report.timeline[1].timestamp = "1999-01-01T00:00:00Z"

    with pytest.raises(AuditReportValidationError, match="earlier than previous"):
        validate_audit_report(report)


def test_validate_rejects_non_consecutive_sequence():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)
    report = generate_report(request, records, events, policies)

    report.timeline[0].sequence = 99

    with pytest.raises(AuditReportValidationError, match="sequence"):
        validate_audit_report(report)


def test_validate_rejects_inconsistent_claim_counts():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)
    report = generate_report(request, records, events, policies)

    report.claim_summaries[0].permit_count = 999

    with pytest.raises(AuditReportValidationError, match="permit_count"):
        validate_audit_report(report)


def test_validate_rejects_inverted_window():
    records, events, policies = _minimal_chain_and_trail()
    request = AuditReportRequest(caller_agent_id=CALLER, callee_agent_id=CALLEE)
    report = generate_report(request, records, events, policies)

    report.from_timestamp = "2099-01-01T00:00:00Z"
    report.to_timestamp = "2026-01-01T00:00:00Z"

    with pytest.raises(AuditReportValidationError, match="inverted"):
        validate_audit_report(report)
