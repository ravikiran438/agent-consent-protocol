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

"""Projector for the audit-projection extension.

Walks the Core consent chain and adherence trail for a specified
``(caller, callee, window)`` scope and produces an ``AuditReport``
with narrative timeline entries, per-claim statistics, and per-version
statistics. The projection is lossless: every narrative entry carries a
back-reference to the signed record it summarizes.

Narrative rendering uses deterministic f-string templates, not a
language model, such that two conformant implementations produce
byte-identical statistical sections for the same input. Narrative prose
may differ across implementations (the proto says so explicitly) but
the cross-references and counts must match.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from acap.types import (
    AdherenceDecision,
    AdherenceEvent,
    ConsentRecord,
    PolicyDocument,
)
from acap.extensions.audit_projection.types import (
    AuditEntry,
    AuditEntryType,
    AuditReport,
    AuditReportRequest,
    ClaimAuditSummary,
    VersionAuditSummary,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _in_window(
    ts: str, start: str | None, end: str | None
) -> bool:
    if start and ts < start:
        return False
    if end and ts > end:
        return False
    return True


def _consent_entry(
    sequence: int, record: ConsentRecord, is_first: bool
) -> AuditEntry:
    entry_type = (
        AuditEntryType.INITIAL_CONSENT
        if is_first
        else AuditEntryType.RECONSENT_POLICY
    )
    claim_count = len(record.parsed_claims)
    disputed = [p.claim_id for p in record.parsed_claims if p.disputed]
    dispute_clause = (
        f", with disputed claims {sorted(disputed)}" if disputed else ""
    )
    action = "accepted" if is_first else "re-consented to"
    narrative = (
        f"Agent {record.caller_agent_id} {action} Agent "
        f"{record.callee_agent_id}'s usage policy "
        f"v{record.policy_version} ({claim_count} claims), "
        f"decision={record.decision.value}{dispute_clause}."
    )
    return AuditEntry(
        sequence=sequence,
        timestamp=record.accepted_at,
        entry_type=entry_type,
        narrative=narrative,
        policy_version=record.policy_version,
        consent_record_id=record.record_id,
        referenced_claim_ids=[p.claim_id for p in record.parsed_claims],
    )


_ADHERENCE_ENTRY_TYPES = {
    AdherenceDecision.PERMIT: AuditEntryType.ADHERENCE_PERMIT,
    AdherenceDecision.DENY: AuditEntryType.ADHERENCE_DENY,
    AdherenceDecision.ESCALATE: AuditEntryType.ADHERENCE_ESCALATE,
}


def _adherence_entry(
    sequence: int,
    event: AdherenceEvent,
    policy_version: str,
) -> AuditEntry:
    narrative = (
        f"Agent evaluated {event.clause_evaluated} before action "
        f"{event.action!r}. Decision: {event.decision.value.upper()}. "
        f"Reasoning: {event.reasoning!r}"
    )
    return AuditEntry(
        sequence=sequence,
        timestamp=event.timestamp,
        entry_type=_ADHERENCE_ENTRY_TYPES[event.decision],
        narrative=narrative,
        policy_version=policy_version,
        adherence_event_id=event.event_id,
        referenced_claim_ids=[event.claim_id],
    )


def _build_claim_summaries(
    events_in_scope: list[AdherenceEvent],
    policies: dict[str, PolicyDocument] | None,
) -> list[ClaimAuditSummary]:
    # Aggregate counts per claim_id
    counts: dict[str, dict] = {}
    for e in events_in_scope:
        entry = counts.setdefault(
            e.claim_id,
            {
                "clause_ref": e.clause_evaluated,
                "rule_type": "",
                "permit": 0,
                "deny": 0,
                "escalate": 0,
            },
        )
        entry[e.decision.value] += 1

    # Enrich with rule_type from policies when available
    if policies:
        for policy in policies.values():
            for claim in policy.claims:
                if claim.claim_id in counts:
                    counts[claim.claim_id]["rule_type"] = claim.rule_type.value
                    counts[claim.claim_id]["clause_ref"] = claim.clause_ref

    summaries = []
    for claim_id, c in counts.items():
        total = c["permit"] + c["deny"] + c["escalate"]
        summaries.append(
            ClaimAuditSummary(
                claim_id=claim_id,
                clause_ref=c["clause_ref"],
                rule_type=c["rule_type"] or "unknown",
                total_evaluations=total,
                permit_count=c["permit"],
                deny_count=c["deny"],
                escalate_count=c["escalate"],
                summary=(
                    f"{c['clause_ref']} evaluated {total} times: "
                    f"{c['permit']} permit, {c['deny']} deny, "
                    f"{c['escalate']} escalate."
                ),
            )
        )
    summaries.sort(key=lambda s: s.claim_id)
    return summaries


def _build_version_summaries(
    records_in_scope: list[ConsentRecord],
    events_in_scope: list[AdherenceEvent],
    policies: dict[str, PolicyDocument] | None,
    window_end: str,
) -> list[VersionAuditSummary]:
    # Map policy_version -> list of ConsentRecords for that version, ordered
    records_by_version: dict[str, list[ConsentRecord]] = {}
    for r in records_in_scope:
        records_by_version.setdefault(r.policy_version, []).append(r)

    # Count adherence events per version using consent_record_id -> version
    version_by_record: dict[str, str] = {
        r.record_id: r.policy_version for r in records_in_scope
    }
    event_counts: dict[str, int] = {}
    for e in events_in_scope:
        version = version_by_record.get(e.consent_record_id)
        if version:
            event_counts[version] = event_counts.get(version, 0) + 1

    # Order versions chronologically by first consent acceptance
    ordered_versions = sorted(
        records_by_version.keys(),
        key=lambda v: records_by_version[v][0].accepted_at,
    )

    summaries = []
    for i, version in enumerate(ordered_versions):
        records = records_by_version[version]
        effective_from = records[0].accepted_at
        if i + 1 < len(ordered_versions):
            effective_until = records_by_version[
                ordered_versions[i + 1]
            ][0].accepted_at
        else:
            effective_until = window_end
        claim_count = (
            len(policies[version].claims)
            if policies and version in policies
            else len(records[0].parsed_claims)
        )
        events = event_counts.get(version, 0)
        summaries.append(
            VersionAuditSummary(
                version=version,
                effective_from=effective_from,
                effective_until=effective_until,
                claim_count=claim_count,
                consent_decision=records[0].decision.value,
                total_adherence_events=events,
                summary=(
                    f"Policy v{version} active from {effective_from} to "
                    f"{effective_until}, decision={records[0].decision.value}, "
                    f"{events} adherence events."
                ),
            )
        )
    return summaries


def _build_executive_summary(
    request: AuditReportRequest,
    records: list[ConsentRecord],
    events: list[AdherenceEvent],
) -> str:
    permit = sum(1 for e in events if e.decision is AdherenceDecision.PERMIT)
    deny = sum(1 for e in events if e.decision is AdherenceDecision.DENY)
    esc = sum(1 for e in events if e.decision is AdherenceDecision.ESCALATE)
    versions = sorted({r.policy_version for r in records})
    versions_str = ", ".join(f"v{v}" for v in versions) if versions else "none"
    return (
        f"Between {request.from_timestamp or 'chain start'} and "
        f"{request.to_timestamp or 'report time'}, Agent "
        f"{request.caller_agent_id} operated under "
        f"{len(versions)} policy version(s) of Agent "
        f"{request.callee_agent_id} ({versions_str}). "
        f"{len(records)} consent record(s) were produced. "
        f"Of {len(events)} adherence event(s), {permit} were permitted, "
        f"{deny} denied, and {esc} escalated."
    )


def generate_report(
    request: AuditReportRequest,
    consent_chain: list[ConsentRecord],
    adherence_trail: list[AdherenceEvent],
    policies: dict[str, PolicyDocument] | None = None,
) -> AuditReport:
    """Project a Core chain and trail into a human-readable AuditReport.

    ``consent_chain`` MUST be ordered oldest-first. ``adherence_trail``
    SHOULD be ordered by timestamp but is re-sorted here to be safe.
    ``policies`` is optional; when supplied it enriches claim summaries
    with rule_type information that cannot be derived from events alone.
    """
    generated_at = _now_iso()

    records_in_scope = [
        r
        for r in consent_chain
        if r.caller_agent_id == request.caller_agent_id
        and r.callee_agent_id == request.callee_agent_id
        and _in_window(r.accepted_at, request.from_timestamp, request.to_timestamp)
        and (
            not request.policy_versions
            or r.policy_version in request.policy_versions
        )
    ]

    record_ids_in_scope = {r.record_id for r in records_in_scope}

    events_in_scope = [
        e
        for e in adherence_trail
        if e.consent_record_id in record_ids_in_scope
        and _in_window(e.timestamp, request.from_timestamp, request.to_timestamp)
        and (not request.claim_ids or e.claim_id in request.claim_ids)
        and (not request.decision_filter or e.decision in request.decision_filter)
    ]
    events_in_scope.sort(key=lambda e: e.timestamp)

    # Build the timeline by merging records and events in timestamp order
    merged: list[tuple[str, str, object]] = []
    for r in records_in_scope:
        merged.append((r.accepted_at, "consent", r))
    for e in events_in_scope:
        merged.append((e.timestamp, "adherence", e))
    merged.sort(key=lambda t: t[0])

    version_by_record = {
        r.record_id: r.policy_version for r in records_in_scope
    }

    timeline: list[AuditEntry] = []
    seen_first_consent = False
    for seq, (_, kind, obj) in enumerate(merged, start=1):
        if kind == "consent":
            record = obj
            is_first = not seen_first_consent
            seen_first_consent = True
            timeline.append(_consent_entry(seq, record, is_first))
        else:
            event = obj
            policy_version = version_by_record.get(
                event.consent_record_id, ""
            )
            timeline.append(_adherence_entry(seq, event, policy_version))

    window_end = request.to_timestamp or generated_at

    return AuditReport(
        report_id=f"report-{uuid.uuid4()}",
        generated_at=generated_at,
        caller_agent_id=request.caller_agent_id,
        callee_agent_id=request.callee_agent_id,
        from_timestamp=(
            request.from_timestamp
            or (records_in_scope[0].accepted_at if records_in_scope else generated_at)
        ),
        to_timestamp=window_end,
        executive_summary=_build_executive_summary(
            request, records_in_scope, events_in_scope
        ),
        timeline=timeline,
        claim_summaries=_build_claim_summaries(events_in_scope, policies),
        version_summaries=_build_version_summaries(
            records_in_scope, events_in_scope, policies, window_end
        ),
    )
