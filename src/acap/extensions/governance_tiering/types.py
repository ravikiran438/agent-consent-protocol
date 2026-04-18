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

"""Types for the governance-tiering extension.

These mirror the messages in ``extensions/governance-tiering/consent.governance.proto``
and compose with the Core types in ``acap.types``:

  - ``PolicyDiff`` is attached to a ``ConsentRecord`` on re-consent.
  - ``EscalationAssessment`` is produced by a governance agent and
    accompanies the re-consent ``ConsentRecord``.
  - ``DelegationChain`` is assembled by an originating caller to
    account for multi-hop A→B→C invocations.

No Core types are modified; the extension lives alongside Core.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimChangeType(str, Enum):
    """How a single PolicyClaim changed across two PolicyDocument versions."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class EscalationTier(str, Enum):
    """Who reviewed and approved a re-consent decision.

    The three tiers correspond to the S8/S9 invariants in the
    ConsentLifecycle TLA+ specification.
    """

    # Governance agent auto-approved an immaterial change.
    AUTO_APPROVED = "auto_approved"

    # Governance agent approved a material change within its delegated
    # authority; human principal was not consulted.
    GOVERNANCE_REVIEWED = "governance_reviewed"

    # Governance agent escalated; human principal must approve before the
    # chain advances. Blocks re-consent until human acts.
    HUMAN_REQUIRED = "human_required"


class ClaimDiff(BaseModel):
    """How a single PolicyClaim changed between two PolicyDocument versions.

    The claim_id refers to the claim in the NEW version when change_type is
    ADDED or MODIFIED, and to the retired claim in the PREVIOUS version when
    change_type is REMOVED. Consumers use clause_ref to correlate modified
    claims across the version bump.
    """

    claim_id: str = Field(
        description="claim_id of the affected PolicyClaim.",
    )
    clause_ref: str = Field(
        description="Human-readable clause reference (e.g. '§3.4.2').",
    )
    change_type: ClaimChangeType = Field(
        description="Whether the claim was added, removed, or modified.",
    )
    summary: str = Field(
        description="Natural-language summary of the change, suitable for "
        "human principal review on escalation.",
    )

    previous_rule_type: Optional[str] = Field(default=None)
    previous_action: Optional[str] = Field(default=None)
    previous_asset: Optional[str] = Field(default=None)
    previous_constraint: Optional[str] = Field(default=None)

    new_rule_type: Optional[str] = Field(default=None)
    new_action: Optional[str] = Field(default=None)
    new_asset: Optional[str] = Field(default=None)
    new_constraint: Optional[str] = Field(default=None)


class PolicyDiff(BaseModel):
    """Ordered summary of how a PolicyDocument changed between two versions.

    Computed by the calling agent immediately after it fetches a new
    PolicyDocument version. Passed to the governance agent as the primary
    input to materiality classification.
    """

    from_version: str = Field(
        description="Semver of the previous PolicyDocument.",
    )
    to_version: str = Field(
        description="Semver of the new PolicyDocument.",
    )
    diffs: list[ClaimDiff] = Field(
        description="Per-claim diffs. At least one entry MUST be present.",
        min_length=1,
    )
    impact_summary: str = Field(
        description="Agent-generated natural-language summary of overall "
        "impact, suitable for presentation to the human principal.",
    )


class MaterialitySignal(BaseModel):
    """One factor in the governance agent's materiality assessment.

    The collection of signals lets auditors understand WHY a particular
    escalation tier was chosen. Each signal is self-describing; the set of
    recognised ``factor`` strings is open so governance agents can introduce
    new heuristics without a schema bump.
    """

    factor: str = Field(
        description="Which aspect of the change this signal evaluates "
        "(e.g. 'new_claim', 'removed_permission', 'rule_type_inversion').",
    )
    assessment: str = Field(
        description="Either 'material' or 'immaterial'.",
    )
    reasoning: str = Field(
        description="Natural-language reasoning for the assessment.",
    )


class EscalationAssessment(BaseModel):
    """Governance agent's complete evaluation of a re-consent event.

    Attached to the ``ConsentRecord`` produced from a re-consent event so
    that the chain carries its own escalation history. A record without an
    assessment is valid only for FIRST consent; Core invariant S8 requires
    every re-consent (chain index ≥ 2) to carry a tier.
    """

    tier: EscalationTier = Field(
        description="Tier determined by the governance agent.",
    )
    governance_agent_id: str = Field(
        description="DID or HTTPS URL identifying the governance agent.",
    )
    assessed_at: str = Field(
        description="ISO 8601 UTC datetime of the assessment.",
    )
    signals: list[MaterialitySignal] = Field(
        description="Signals supporting the tier decision. At least one.",
        min_length=1,
    )
    summary: str = Field(
        description="Natural-language summary of the overall assessment.",
    )
    principal_notified: bool = Field(
        description="Whether the human principal was notified, even if not "
        "required to act. Callees under EU AI Act obligations may require "
        "notification at all tiers.",
    )
    reviewed_by: Optional[str] = Field(
        default=None,
        description="DID or HTTPS URL of the human principal who reviewed. "
        "REQUIRED when tier is HUMAN_REQUIRED.",
    )
    reviewed_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC datetime of human review. REQUIRED when "
        "tier is HUMAN_REQUIRED.",
    )
    governance_signature: Optional[str] = Field(
        default=None,
        description="JWS signature of the governance agent over this "
        "assessment. RECOMMENDED for non-repudiation.",
    )


class DelegationHop(BaseModel):
    """One caller→callee edge in a multi-hop consent path.

    Each hop carries its own escalation tier because materiality is
    evaluated against the governance meta-policy of the hop's principal,
    and two principals can disagree about what is material.
    """

    caller_agent_id: str = Field(
        description="DID or HTTPS URL of the caller at this hop.",
    )
    callee_agent_id: str = Field(
        description="DID or HTTPS URL of the callee at this hop.",
    )
    consent_record_id: str = Field(
        description="record_id of the ConsentRecord governing this hop.",
    )
    tier: EscalationTier = Field(
        description="Escalation tier applied at this hop.",
    )
    principal_id: Optional[str] = Field(
        default=None,
        description="Human principal on whose behalf the caller is acting.",
    )


class DelegationChain(BaseModel):
    """Origin-first ordered sequence of delegation hops.

    Exists to let an auditor reason about end-to-end consent for an
    Agent A → Agent B → Agent C (or longer) path without re-walking every
    caller–callee pair's individual ConsentRecord history.
    """

    origin_principal_id: str = Field(
        description="DID or HTTPS URL of the originating human principal.",
    )
    hops: list[DelegationHop] = Field(
        description="Origin-first ordered hops. At least one entry.",
        min_length=1,
    )
    origin_consent_record_id: str = Field(
        description="record_id of the ConsentRecord at the first hop.",
    )
    assembled_at: str = Field(
        description="ISO 8601 UTC datetime when the chain was assembled.",
    )
