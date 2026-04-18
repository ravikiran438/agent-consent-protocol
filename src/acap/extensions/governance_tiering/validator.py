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

"""Runtime validators for governance-tiering invariants.

Mirrors ConsentLifecycle.tla invariants S8 (``GovernanceAlwaysReviews``)
and S9 (``HumanRequiredHonoured``). Structural type checks (non-empty
signals, non-empty hops) are enforced by Pydantic at construction time
and not re-checked here.
"""

from __future__ import annotations

from acap.extensions.governance_tiering.types import (
    DelegationChain,
    EscalationAssessment,
    EscalationTier,
)


class GovernanceValidationError(ValueError):
    """Raised when governance-tiering invariants are violated."""


def validate_escalation_assessment(assessment: EscalationAssessment) -> None:
    """Validate an EscalationAssessment.

    S9: HUMAN_REQUIRED requires ``reviewed_by``, ``reviewed_at``, and
    ``principal_notified``. ``reviewed_at`` must not precede
    ``assessed_at``.
    """
    if assessment.tier is EscalationTier.HUMAN_REQUIRED:
        if not assessment.reviewed_by:
            raise GovernanceValidationError(
                "tier HUMAN_REQUIRED requires reviewed_by"
            )
        if not assessment.reviewed_at:
            raise GovernanceValidationError(
                "tier HUMAN_REQUIRED requires reviewed_at"
            )
        if not assessment.principal_notified:
            raise GovernanceValidationError(
                "tier HUMAN_REQUIRED requires principal_notified=True"
            )

    if (
        assessment.reviewed_at
        and assessment.reviewed_at < assessment.assessed_at
    ):
        raise GovernanceValidationError(
            f"reviewed_at {assessment.reviewed_at!r} precedes "
            f"assessed_at {assessment.assessed_at!r}"
        )


def validate_delegation_chain(chain: DelegationChain) -> None:
    """Validate a DelegationChain for structural coherence.

    Checks origin anchoring (hops[0] matches origin_consent_record_id and
    origin_principal_id) and contiguity (every hop's caller equals the
    previous hop's callee).
    """
    first = chain.hops[0]
    if first.consent_record_id != chain.origin_consent_record_id:
        raise GovernanceValidationError(
            f"origin_consent_record_id {chain.origin_consent_record_id!r} "
            f"does not match hops[0].consent_record_id "
            f"{first.consent_record_id!r}"
        )
    if first.principal_id and first.principal_id != chain.origin_principal_id:
        raise GovernanceValidationError(
            f"origin_principal_id {chain.origin_principal_id!r} does not "
            f"match hops[0].principal_id {first.principal_id!r}"
        )

    for i, hop in enumerate(chain.hops):
        if i == 0:
            continue
        prev = chain.hops[i - 1]
        if hop.caller_agent_id != prev.callee_agent_id:
            raise GovernanceValidationError(
                f"hop {i} caller {hop.caller_agent_id!r} does not match "
                f"hop {i - 1} callee {prev.callee_agent_id!r}; chain is "
                "not contiguous"
            )
