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

"""Structural validator for the audit-projection extension.

Checks invariants an auditor relies on: timeline chronology, 1-based
sequential indexing, per-claim count consistency with the timeline,
and presence of at least one back-reference on every entry.
"""

from __future__ import annotations

from acap.extensions.audit_projection.types import AuditReport, AuditEntryType


class AuditReportValidationError(ValueError):
    """Raised when an AuditReport violates structural invariants."""


_ADHERENCE_ENTRY_TYPES = {
    AuditEntryType.ADHERENCE_PERMIT: "permit_count",
    AuditEntryType.ADHERENCE_DENY: "deny_count",
    AuditEntryType.ADHERENCE_ESCALATE: "escalate_count",
}


def validate_audit_report(report: AuditReport) -> None:
    """Enforce structural well-formedness on an AuditReport."""
    for i, entry in enumerate(report.timeline):
        expected = i + 1
        if entry.sequence != expected:
            raise AuditReportValidationError(
                f"timeline entry at index {i} has sequence "
                f"{entry.sequence}; expected {expected}"
            )
        if i > 0 and entry.timestamp < report.timeline[i - 1].timestamp:
            raise AuditReportValidationError(
                f"timeline entry {entry.sequence} timestamp "
                f"{entry.timestamp!r} is earlier than previous entry "
                f"{report.timeline[i - 1].timestamp!r}"
            )
        if not entry.consent_record_id and not entry.adherence_event_id:
            raise AuditReportValidationError(
                f"timeline entry {entry.sequence} has no "
                "consent_record_id or adherence_event_id back-reference"
            )

    if report.from_timestamp > report.to_timestamp:
        raise AuditReportValidationError(
            f"report window is inverted: from={report.from_timestamp!r} "
            f"to={report.to_timestamp!r}"
        )

    # Claim summaries must match timeline counts
    timeline_claim_counts: dict[str, dict[str, int]] = {}
    for entry in report.timeline:
        field = _ADHERENCE_ENTRY_TYPES.get(entry.entry_type)
        if field is None:
            continue
        for claim_id in entry.referenced_claim_ids:
            counts = timeline_claim_counts.setdefault(
                claim_id, {"permit_count": 0, "deny_count": 0, "escalate_count": 0}
            )
            counts[field] += 1

    for summary in report.claim_summaries:
        expected = timeline_claim_counts.get(
            summary.claim_id,
            {"permit_count": 0, "deny_count": 0, "escalate_count": 0},
        )
        for field, count in expected.items():
            if getattr(summary, field) != count:
                raise AuditReportValidationError(
                    f"claim summary for {summary.claim_id} has "
                    f"{field}={getattr(summary, field)}; timeline shows "
                    f"{count}"
                )
        total = (
            summary.permit_count + summary.deny_count + summary.escalate_count
        )
        if summary.total_evaluations != total:
            raise AuditReportValidationError(
                f"claim summary for {summary.claim_id} has "
                f"total_evaluations={summary.total_evaluations}; sum of "
                f"permit/deny/escalate is {total}"
            )
