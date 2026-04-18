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

"""Types for the audit-projection extension.

Mirrors the messages in ``extensions/audit-projection/consent.audit.proto``.
An ``AuditReport`` is the projection of Core records into narrative form
for a stated ``(caller, callee, time window)`` scope.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from acap.types import AdherenceDecision


class AuditEntryType(str, Enum):
    """Categorizes each timeline entry for regulator-facing filtering."""

    INITIAL_CONSENT = "initial_consent"
    RECONSENT_POLICY = "reconsent_policy"
    RECONSENT_CAPABILITY = "reconsent_capability"
    ADHERENCE_PERMIT = "adherence_permit"
    ADHERENCE_DENY = "adherence_deny"
    ADHERENCE_ESCALATE = "adherence_escalate"
    GOVERNANCE_AUTO = "governance_auto"
    GOVERNANCE_REVIEWED = "governance_reviewed"
    HUMAN_REVIEW = "human_review"
    CONSENT_INVALIDATED = "consent_invalidated"


class AuditReportRequest(BaseModel):
    """Scope specification for a report."""

    caller_agent_id: str = Field(
        description="DID or HTTPS URL of the calling agent.",
    )
    callee_agent_id: str = Field(
        description="DID or HTTPS URL of the callee agent.",
    )
    from_timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC start of the audit window. Absent means "
        "'from the first record'.",
    )
    to_timestamp: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC end of the audit window. Absent means "
        "'up to the current time'.",
    )
    policy_versions: list[str] = Field(
        default_factory=list,
        description="Restrict to specific policy versions. Empty means all.",
    )
    claim_ids: list[str] = Field(
        default_factory=list,
        description="Restrict to specific claim ids. Empty means all.",
    )
    decision_filter: list[AdherenceDecision] = Field(
        default_factory=list,
        description="Restrict to specific adherence decisions. Empty means all.",
    )
    language: str = Field(
        default="en",
        description="Output language (BCP 47 tag). The reference "
        "implementation supports 'en' only; other values are accepted "
        "but rendered in English.",
    )


class AuditEntry(BaseModel):
    """One timeline event, rendered as narrative with machine cross-refs."""

    sequence: int = Field(
        description="Chronological index in the timeline (1-based).",
    )
    timestamp: str = Field(
        description="ISO 8601 UTC datetime of the event.",
    )
    entry_type: AuditEntryType = Field(
        description="What kind of event this is.",
    )
    narrative: str = Field(
        description="Plain-English description, suitable for a regulator.",
    )
    policy_version: str = Field(
        description="PolicyDocument version active at the time of the event.",
    )
    consent_record_id: Optional[str] = Field(
        default=None,
        description="Back-reference to the source ConsentRecord, if any.",
    )
    adherence_event_id: Optional[str] = Field(
        default=None,
        description="Back-reference to the source AdherenceEvent, if any.",
    )
    referenced_claim_ids: list[str] = Field(
        default_factory=list,
        description="Claim ids this entry references.",
    )


class ClaimAuditSummary(BaseModel):
    """Per-claim statistics over the audit window."""

    claim_id: str = Field(description="Stable claim id.")
    clause_ref: str = Field(description="Human-readable clause reference.")
    rule_type: str = Field(
        description="Rule type (permission, prohibition, obligation).",
    )
    total_evaluations: int = Field(
        description="Total adherence events referencing this claim.",
    )
    permit_count: int = Field(description="Events with decision=permit.")
    deny_count: int = Field(description="Events with decision=deny.")
    escalate_count: int = Field(description="Events with decision=escalate.")
    summary: str = Field(description="Plain-English summary.")


class VersionAuditSummary(BaseModel):
    """Per-policy-version statistics."""

    version: str = Field(description="Policy semver.")
    effective_from: str = Field(description="ISO 8601 UTC start of activity.")
    effective_until: str = Field(
        description="ISO 8601 UTC end of activity, or the report end "
        "timestamp if still active.",
    )
    claim_count: int = Field(description="Claims in this version.")
    consent_decision: str = Field(
        description="The caller's decision on this version.",
    )
    total_adherence_events: int = Field(
        description="Adherence events recorded under this version.",
    )
    summary: str = Field(description="Plain-English summary.")


class AuditReport(BaseModel):
    """Structured human-readable report for one caller-callee pair."""

    report_id: str = Field(description="Unique id for this report.")
    generated_at: str = Field(description="ISO 8601 UTC generation time.")
    caller_agent_id: str = Field(description="DID or HTTPS URL of the caller.")
    callee_agent_id: str = Field(description="DID or HTTPS URL of the callee.")
    from_timestamp: str = Field(description="Report window start.")
    to_timestamp: str = Field(description="Report window end.")
    executive_summary: str = Field(
        description="2-3 paragraph plain-English overview.",
    )
    timeline: list[AuditEntry] = Field(
        description="Chronological timeline of all consent and adherence "
        "events in scope.",
    )
    claim_summaries: list[ClaimAuditSummary] = Field(
        description="Per-claim statistical breakdown.",
    )
    version_summaries: list[VersionAuditSummary] = Field(
        description="Per-policy-version statistical breakdown.",
    )
