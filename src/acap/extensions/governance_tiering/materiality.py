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

"""Reference materiality classifier for governance-tiering.

Diffs two ``PolicyDocument`` versions and classifies the diff into an
``EscalationTier``. Downstream implementations (guardian extension,
commercial governance agents) are expected to extend this with semantic
reasoning; the structural signals here are the floor.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from enum import Enum

from acap.types import PolicyClaim, PolicyDocument
from acap.extensions.governance_tiering.types import (
    ClaimChangeType,
    ClaimDiff,
    EscalationAssessment,
    EscalationTier,
    MaterialitySignal,
    PolicyDiff,
)


class MaterialityFactor(str, Enum):
    """Closed set of structural signals the reference classifier emits."""

    NEW_CLAIM = "new_claim"
    REMOVED_CLAIM = "removed_claim"
    MODIFIED_CLAIM = "modified_claim"
    RULE_TYPE_INVERSION = "rule_type_inversion"
    CONSTRAINT_RELAXED = "constraint_relaxed"
    ESCALATE_ON_DENY_ADDED = "escalate_on_deny_added"


# Any of these firing forces HUMAN_REQUIRED. The other factors force at
# least GOVERNANCE_REVIEWED. Baked in, not configurable; downstream agents
# that want a different policy should override `classify`.
_HUMAN_REQUIRED_FACTORS = frozenset({
    MaterialityFactor.REMOVED_CLAIM.value,
    MaterialityFactor.RULE_TYPE_INVERSION.value,
    MaterialityFactor.CONSTRAINT_RELAXED.value,
    MaterialityFactor.ESCALATE_ON_DENY_ADDED.value,
})


def diff_policies(prev: PolicyDocument, curr: PolicyDocument) -> PolicyDiff:
    """Return a structural diff between two PolicyDocument versions.

    Raises ``ValueError`` if versions match or if no structural changes
    are detected (metadata-only bumps are out of scope for the classifier).
    """
    if prev.version == curr.version:
        raise ValueError(
            f"cannot diff policies that share version {prev.version!r}"
        )

    prev_claims = {c.claim_id: c for c in prev.claims}
    curr_claims = {c.claim_id: c for c in curr.claims}

    diffs: list[ClaimDiff] = []
    for claim_id, claim in curr_claims.items():
        if claim_id not in prev_claims:
            diffs.append(_added(claim))
            continue
        mod = _modified(prev_claims[claim_id], claim)
        if mod is not None:
            diffs.append(mod)
    for claim_id, claim in prev_claims.items():
        if claim_id not in curr_claims:
            diffs.append(_removed(claim))

    if not diffs:
        raise ValueError(
            f"no structural changes between v{prev.version} and v{curr.version}"
        )

    counts = Counter(d.change_type for d in diffs)
    impact = (
        f"v{prev.version} → v{curr.version}: "
        f"{counts[ClaimChangeType.ADDED]} added, "
        f"{counts[ClaimChangeType.REMOVED]} removed, "
        f"{counts[ClaimChangeType.MODIFIED]} modified."
    )
    return PolicyDiff(
        from_version=prev.version,
        to_version=curr.version,
        diffs=diffs,
        impact_summary=impact,
    )


def _added(c: PolicyClaim) -> ClaimDiff:
    return ClaimDiff(
        claim_id=c.claim_id,
        clause_ref=c.clause_ref,
        change_type=ClaimChangeType.ADDED,
        summary=f"New {c.rule_type.value} at {c.clause_ref}: {c.action} on {c.asset}",
        new_rule_type=c.rule_type.value,
        new_action=c.action,
        new_asset=c.asset,
        new_constraint=c.constraint,
    )


def _removed(c: PolicyClaim) -> ClaimDiff:
    return ClaimDiff(
        claim_id=c.claim_id,
        clause_ref=c.clause_ref,
        change_type=ClaimChangeType.REMOVED,
        summary=f"Removed {c.rule_type.value} at {c.clause_ref}: {c.action} on {c.asset}",
        previous_rule_type=c.rule_type.value,
        previous_action=c.action,
        previous_asset=c.asset,
        previous_constraint=c.constraint,
    )


def _modified(prev: PolicyClaim, curr: PolicyClaim) -> ClaimDiff | None:
    before = (
        prev.rule_type, prev.action, prev.asset, prev.constraint,
        prev.escalate_on_deny,
    )
    after = (
        curr.rule_type, curr.action, curr.asset, curr.constraint,
        curr.escalate_on_deny,
    )
    if before == after:
        return None
    return ClaimDiff(
        claim_id=curr.claim_id,
        clause_ref=curr.clause_ref,
        change_type=ClaimChangeType.MODIFIED,
        summary=f"Modified {curr.rule_type.value} at {curr.clause_ref}: "
        f"{curr.action} on {curr.asset}",
        previous_rule_type=prev.rule_type.value,
        previous_action=prev.action,
        previous_asset=prev.asset,
        previous_constraint=prev.constraint,
        new_rule_type=curr.rule_type.value,
        new_action=curr.action,
        new_asset=curr.asset,
        new_constraint=curr.constraint,
    )


def _collect_signals(
    diff: PolicyDiff,
    prev_claims: dict[str, PolicyClaim],
    curr_claims: dict[str, PolicyClaim],
) -> list[MaterialitySignal]:
    signals: list[MaterialitySignal] = []
    for d in diff.diffs:
        if d.change_type is ClaimChangeType.ADDED:
            signals.append(_signal(
                MaterialityFactor.NEW_CLAIM,
                f"Claim {d.claim_id} at {d.clause_ref} is new in "
                f"v{diff.to_version}.",
            ))
        elif d.change_type is ClaimChangeType.REMOVED:
            signals.append(_signal(
                MaterialityFactor.REMOVED_CLAIM,
                f"Claim {d.claim_id} at {d.clause_ref} was removed.",
            ))
        else:
            signals.append(_signal(
                MaterialityFactor.MODIFIED_CLAIM,
                f"Claim {d.claim_id} at {d.clause_ref} was modified.",
            ))
            if d.previous_rule_type != d.new_rule_type:
                signals.append(_signal(
                    MaterialityFactor.RULE_TYPE_INVERSION,
                    f"Claim {d.claim_id} rule_type changed from "
                    f"{d.previous_rule_type!r} to {d.new_rule_type!r}.",
                ))
            if d.previous_constraint is not None and not d.new_constraint:
                signals.append(_signal(
                    MaterialityFactor.CONSTRAINT_RELAXED,
                    f"Claim {d.claim_id} constraint "
                    f"{d.previous_constraint!r} was removed.",
                ))

        prev = prev_claims.get(d.claim_id)
        curr = curr_claims.get(d.claim_id)
        if _escalate_on_deny_added(prev, curr):
            signals.append(_signal(
                MaterialityFactor.ESCALATE_ON_DENY_ADDED,
                f"Claim {d.claim_id} now carries escalate_on_deny.",
            ))

    return signals


def _escalate_on_deny_added(
    prev: PolicyClaim | None, curr: PolicyClaim | None
) -> bool:
    return bool(curr and curr.escalate_on_deny) and not bool(
        prev and prev.escalate_on_deny
    )


def _signal(factor: MaterialityFactor, reasoning: str) -> MaterialitySignal:
    return MaterialitySignal(
        factor=factor.value, assessment="material", reasoning=reasoning
    )


def _tier(signals: list[MaterialitySignal]) -> EscalationTier:
    fired = {s.factor for s in signals}
    if fired & _HUMAN_REQUIRED_FACTORS:
        return EscalationTier.HUMAN_REQUIRED
    if fired:
        return EscalationTier.GOVERNANCE_REVIEWED
    return EscalationTier.AUTO_APPROVED


def classify(
    prev: PolicyDocument,
    curr: PolicyDocument,
    *,
    governance_agent_id: str,
) -> tuple[PolicyDiff, EscalationAssessment]:
    """Diff two policies and produce a tiered EscalationAssessment.

    Callers set ``reviewed_by`` / ``reviewed_at`` on the returned
    assessment after the human review step, if the tier demands it.
    """
    diff = diff_policies(prev, curr)
    prev_claims = {c.claim_id: c for c in prev.claims}
    curr_claims = {c.claim_id: c for c in curr.claims}
    signals = _collect_signals(diff, prev_claims, curr_claims)
    tier = _tier(signals)

    fired = sorted({s.factor for s in signals})
    assessment = EscalationAssessment(
        tier=tier,
        governance_agent_id=governance_agent_id,
        assessed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        signals=signals,
        summary=f"Tier {tier.value} for {diff.from_version}→{diff.to_version}. "
        f"Material signals: {', '.join(fired) or 'none'}.",
        principal_notified=(tier is EscalationTier.HUMAN_REQUIRED),
    )
    return diff, assessment
