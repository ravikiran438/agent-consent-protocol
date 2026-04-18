# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for the governance-tiering extension.

Covers the reference materiality classifier and runtime validators,
exercising the S8/S9 invariants from ConsentLifecycle.tla.
"""

from __future__ import annotations

import pytest

from acap.extensions.governance_tiering import (
    ClaimChangeType,
    DelegationChain,
    DelegationHop,
    EscalationAssessment,
    EscalationTier,
    GovernanceValidationError,
    MaterialityFactor,
    MaterialitySignal,
    classify,
    diff_policies,
    validate_delegation_chain,
    validate_escalation_assessment,
)
from acap.types import PolicyClaim, PolicyDocument, RuleType


GOV_AGENT = "did:agent:governance"
CALLER = "did:agent:caller"
CALLEE_A = "https://callee-a.example.com"
CALLEE_B = "https://callee-b.example.com"


def _policy(version: str, claims: list[PolicyClaim]) -> PolicyDocument:
    return PolicyDocument(
        version=version,
        document_uri=f"https://callee.example.com/policy/{version}.json",
        document_hash=f"sha256:{'0' * 64}",
        effective_date="2026-04-01T00:00:00Z",
        claims=claims,
        publisher=CALLEE_A,
        natural_language_uri="https://callee.example.com/terms",
    )


def _claim(
    claim_id: str,
    *,
    rule: RuleType = RuleType.PROHIBITION,
    constraint: str | None = None,
    escalate_on_deny: bool | None = None,
    action: str = "odrl:aggregate",
    asset: str = "pii:session_data",
) -> PolicyClaim:
    return PolicyClaim(
        claim_id=claim_id,
        clause_ref=f"§{claim_id[-1]}",
        action=action,
        asset=asset,
        rule_type=rule,
        constraint=constraint,
        effective_version="1.0.0",
        escalate_on_deny=escalate_on_deny,
    )


# ─────────────────────────────────────────────────────────────────────────────
# diff_policies
# ─────────────────────────────────────────────────────────────────────────────


def test_diff_policies_rejects_same_version():
    p = _policy("1.0.0", [_claim("a")])
    with pytest.raises(ValueError, match="share version"):
        diff_policies(p, p)


def test_diff_policies_rejects_no_structural_change():
    prev = _policy("1.0.0", [_claim("a")])
    curr = _policy("2.0.0", [_claim("a")])
    with pytest.raises(ValueError, match="no structural changes"):
        diff_policies(prev, curr)


def test_diff_policies_detects_added_claim():
    prev = _policy("1.0.0", [_claim("a")])
    curr = _policy("2.0.0", [_claim("a"), _claim("b")])
    diff = diff_policies(prev, curr)

    assert diff.from_version == "1.0.0"
    assert diff.to_version == "2.0.0"
    added = [d for d in diff.diffs if d.change_type is ClaimChangeType.ADDED]
    assert [d.claim_id for d in added] == ["b"]


def test_diff_policies_detects_removed_claim():
    prev = _policy("1.0.0", [_claim("a"), _claim("b")])
    curr = _policy("2.0.0", [_claim("a")])
    diff = diff_policies(prev, curr)
    removed = [d for d in diff.diffs if d.change_type is ClaimChangeType.REMOVED]
    assert [d.claim_id for d in removed] == ["b"]


def test_diff_policies_detects_modified_claim():
    prev = _policy("1.0.0", [_claim("a", rule=RuleType.PROHIBITION)])
    curr = _policy("2.0.0", [_claim("a", rule=RuleType.PERMISSION)])
    diff = diff_policies(prev, curr)
    modified = [d for d in diff.diffs if d.change_type is ClaimChangeType.MODIFIED]
    assert len(modified) == 1
    m = modified[0]
    assert m.previous_rule_type == "prohibition"
    assert m.new_rule_type == "permission"


# ─────────────────────────────────────────────────────────────────────────────
# classify — tier selection
# ─────────────────────────────────────────────────────────────────────────────


def test_classify_governance_reviewed_when_only_new_claim():
    prev = _policy("1.0.0", [_claim("a")])
    curr = _policy("2.0.0", [_claim("a"), _claim("b")])

    _, assessment = classify(prev, curr, governance_agent_id=GOV_AGENT)
    assert assessment.tier is EscalationTier.GOVERNANCE_REVIEWED
    fired = {s.factor for s in assessment.signals}
    assert MaterialityFactor.NEW_CLAIM.value in fired


def test_classify_human_required_on_removed_claim():
    prev = _policy("1.0.0", [_claim("a"), _claim("b")])
    curr = _policy("2.0.0", [_claim("a")])

    _, assessment = classify(prev, curr, governance_agent_id=GOV_AGENT)
    assert assessment.tier is EscalationTier.HUMAN_REQUIRED
    assert assessment.principal_notified
    fired = {s.factor for s in assessment.signals}
    assert MaterialityFactor.REMOVED_CLAIM.value in fired


def test_classify_human_required_on_rule_type_inversion():
    prev = _policy("1.0.0", [_claim("a", rule=RuleType.PROHIBITION)])
    curr = _policy("2.0.0", [_claim("a", rule=RuleType.PERMISSION)])

    _, assessment = classify(prev, curr, governance_agent_id=GOV_AGENT)
    assert assessment.tier is EscalationTier.HUMAN_REQUIRED
    fired = {s.factor for s in assessment.signals}
    assert MaterialityFactor.RULE_TYPE_INVERSION.value in fired


def test_classify_human_required_on_constraint_removal():
    prev = _policy(
        "1.0.0",
        [_claim("a", constraint="odrl:purpose eq research_only")],
    )
    curr = _policy("2.0.0", [_claim("a", constraint=None)])

    _, assessment = classify(prev, curr, governance_agent_id=GOV_AGENT)
    assert assessment.tier is EscalationTier.HUMAN_REQUIRED
    fired = {s.factor for s in assessment.signals}
    assert MaterialityFactor.CONSTRAINT_RELAXED.value in fired


def test_classify_human_required_on_escalate_on_deny_added():
    prev = _policy("1.0.0", [_claim("a", escalate_on_deny=False)])
    curr = _policy("2.0.0", [_claim("a", escalate_on_deny=True)])

    _, assessment = classify(prev, curr, governance_agent_id=GOV_AGENT)
    assert assessment.tier is EscalationTier.HUMAN_REQUIRED
    fired = {s.factor for s in assessment.signals}
    assert MaterialityFactor.ESCALATE_ON_DENY_ADDED.value in fired


def test_classify_human_required_on_new_claim_with_escalate_on_deny():
    prev = _policy("1.0.0", [_claim("a")])
    curr = _policy(
        "2.0.0", [_claim("a"), _claim("b", escalate_on_deny=True)]
    )

    _, assessment = classify(prev, curr, governance_agent_id=GOV_AGENT)
    assert assessment.tier is EscalationTier.HUMAN_REQUIRED


def test_classify_modified_claim_emits_umbrella_signal():
    # action-only change: not in the HUMAN_REQUIRED set, so governance_reviewed.
    prev = _policy("1.0.0", [_claim("a", action="odrl:aggregate")])
    curr = _policy("2.0.0", [_claim("a", action="odrl:collect")])

    _, assessment = classify(prev, curr, governance_agent_id=GOV_AGENT)
    assert assessment.tier is EscalationTier.GOVERNANCE_REVIEWED
    fired = {s.factor for s in assessment.signals}
    assert MaterialityFactor.MODIFIED_CLAIM.value in fired


# ─────────────────────────────────────────────────────────────────────────────
# validate_escalation_assessment
# ─────────────────────────────────────────────────────────────────────────────


def _assessment(
    *,
    tier: EscalationTier,
    reviewed_by: str | None = None,
    reviewed_at: str | None = None,
    principal_notified: bool = False,
    assessed_at: str = "2026-04-18T11:00:00Z",
) -> EscalationAssessment:
    return EscalationAssessment(
        tier=tier,
        governance_agent_id=GOV_AGENT,
        assessed_at=assessed_at,
        signals=[
            MaterialitySignal(
                factor="test", assessment="material", reasoning="test"
            )
        ],
        summary="test",
        principal_notified=principal_notified,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
    )


def test_validate_auto_approved_is_ok():
    validate_escalation_assessment(
        _assessment(tier=EscalationTier.AUTO_APPROVED)
    )


def test_validate_governance_reviewed_is_ok():
    validate_escalation_assessment(
        _assessment(tier=EscalationTier.GOVERNANCE_REVIEWED)
    )


def test_validate_human_required_without_reviewer_fails():
    with pytest.raises(GovernanceValidationError, match="reviewed_by"):
        validate_escalation_assessment(
            _assessment(
                tier=EscalationTier.HUMAN_REQUIRED,
                principal_notified=True,
                reviewed_at="2026-04-18T12:00:00Z",
            )
        )


def test_validate_human_required_without_review_time_fails():
    with pytest.raises(GovernanceValidationError, match="reviewed_at"):
        validate_escalation_assessment(
            _assessment(
                tier=EscalationTier.HUMAN_REQUIRED,
                principal_notified=True,
                reviewed_by="did:human:ravi",
            )
        )


def test_validate_human_required_without_notification_fails():
    with pytest.raises(GovernanceValidationError, match="principal_notified"):
        validate_escalation_assessment(
            _assessment(
                tier=EscalationTier.HUMAN_REQUIRED,
                principal_notified=False,
                reviewed_by="did:human:ravi",
                reviewed_at="2026-04-18T12:00:00Z",
            )
        )


def test_validate_human_required_complete_is_ok():
    validate_escalation_assessment(
        _assessment(
            tier=EscalationTier.HUMAN_REQUIRED,
            principal_notified=True,
            reviewed_by="did:human:ravi",
            reviewed_at="2026-04-18T12:00:00Z",
        )
    )


def test_validate_rejects_review_before_assessment():
    with pytest.raises(GovernanceValidationError, match="precedes"):
        validate_escalation_assessment(
            _assessment(
                tier=EscalationTier.HUMAN_REQUIRED,
                principal_notified=True,
                reviewed_by="did:human:ravi",
                assessed_at="2026-04-18T12:00:00Z",
                reviewed_at="2026-04-18T10:00:00Z",
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# validate_delegation_chain
# ─────────────────────────────────────────────────────────────────────────────


def _chain(hops: list[DelegationHop]) -> DelegationChain:
    return DelegationChain(
        origin_principal_id="did:human:ravi",
        hops=hops,
        origin_consent_record_id=hops[0].consent_record_id,
        assembled_at="2026-04-18T12:00:00Z",
    )


def test_validate_chain_single_hop_ok():
    validate_delegation_chain(_chain([
        DelegationHop(
            caller_agent_id=CALLER,
            callee_agent_id=CALLEE_A,
            consent_record_id="rec-1",
            tier=EscalationTier.AUTO_APPROVED,
            principal_id="did:human:ravi",
        )
    ]))


def test_validate_chain_multi_hop_contiguous_ok():
    validate_delegation_chain(_chain([
        DelegationHop(
            caller_agent_id=CALLER,
            callee_agent_id=CALLEE_A,
            consent_record_id="rec-1",
            tier=EscalationTier.GOVERNANCE_REVIEWED,
            principal_id="did:human:ravi",
        ),
        DelegationHop(
            caller_agent_id=CALLEE_A,
            callee_agent_id=CALLEE_B,
            consent_record_id="rec-2",
            tier=EscalationTier.AUTO_APPROVED,
        ),
    ]))


def test_validate_chain_broken_contiguity_rejected():
    chain = _chain([
        DelegationHop(
            caller_agent_id=CALLER,
            callee_agent_id=CALLEE_A,
            consent_record_id="rec-1",
            tier=EscalationTier.AUTO_APPROVED,
        ),
        DelegationHop(
            caller_agent_id="https://some-other-agent.example.com",
            callee_agent_id=CALLEE_B,
            consent_record_id="rec-2",
            tier=EscalationTier.AUTO_APPROVED,
        ),
    ])
    with pytest.raises(GovernanceValidationError, match="contiguous"):
        validate_delegation_chain(chain)


def test_validate_chain_origin_record_mismatch_rejected():
    hops = [
        DelegationHop(
            caller_agent_id=CALLER,
            callee_agent_id=CALLEE_A,
            consent_record_id="rec-1",
            tier=EscalationTier.AUTO_APPROVED,
        )
    ]
    chain = DelegationChain(
        origin_principal_id="did:human:ravi",
        hops=hops,
        origin_consent_record_id="rec-DIFFERENT",
        assembled_at="2026-04-18T12:00:00Z",
    )
    with pytest.raises(
        GovernanceValidationError, match="origin_consent_record_id"
    ):
        validate_delegation_chain(chain)


def test_validate_chain_origin_principal_mismatch_rejected():
    hops = [
        DelegationHop(
            caller_agent_id=CALLER,
            callee_agent_id=CALLEE_A,
            consent_record_id="rec-1",
            tier=EscalationTier.AUTO_APPROVED,
            principal_id="did:human:not-ravi",
        )
    ]
    chain = DelegationChain(
        origin_principal_id="did:human:ravi",
        hops=hops,
        origin_consent_record_id="rec-1",
        assembled_at="2026-04-18T12:00:00Z",
    )
    with pytest.raises(GovernanceValidationError, match="origin_principal_id"):
        validate_delegation_chain(chain)
