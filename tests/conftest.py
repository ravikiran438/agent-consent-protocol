# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Shared fixtures for validator tests.

Keeps the test files focused on assertions rather than plumbing.
"""

from __future__ import annotations

import pytest

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
from acap.validators.hash import compute_policy_hash


CALLER = "did:agent:caller"
CALLEE = "https://callee.example.com/agent"


def _claim(claim_id: str, *, rule: RuleType = RuleType.PROHIBITION) -> PolicyClaim:
    return PolicyClaim(
        claim_id=claim_id,
        clause_ref=f"§{claim_id[-1]}",
        action="odrl:aggregate",
        asset="pii:session_data",
        rule_type=rule,
        effective_version="1.0.0",
    )


@pytest.fixture
def policy_v1() -> PolicyDocument:
    """Minimal but realistic PolicyDocument with three claims."""
    return PolicyDocument(
        version="1.0.0",
        document_uri="https://callee.example.com/.well-known/usage-policy.json",
        document_hash="sha256:placeholder",  # replaced by fixture below
        effective_date="2026-04-01T00:00:00Z",
        claims=[_claim("claim-a"), _claim("claim-b"), _claim("claim-c")],
        publisher=CALLEE,
        natural_language_uri="https://callee.example.com/terms",
        jurisdictions=["EU AI Act"],
    )


@pytest.fixture
def policy_v1_hashed(policy_v1: PolicyDocument) -> PolicyDocument:
    """Same as policy_v1 but with document_hash set to the true hash.

    Most tests want the policy's hash field to actually be correct;
    a few (tamper tests) want the unhashed version, use policy_v1 for those.
    """
    policy_v1.document_hash = compute_policy_hash(policy_v1)
    return policy_v1


def _parsed(claim_id: str, *, disputed: bool = False) -> ParsedClaim:
    return ParsedClaim(
        claim_id=claim_id,
        understood=True,
        disputed=disputed,
        dispute_reason="ambiguous scope" if disputed else None,
    )


@pytest.fixture
def first_record(policy_v1_hashed: PolicyDocument) -> ConsentRecord:
    """First (head-of-chain) ConsentRecord, accepting all three claims."""
    return ConsentRecord(
        record_id="rec-1",
        prev_record_id=None,
        caller_agent_id=CALLER,
        callee_agent_id=CALLEE,
        policy_version=policy_v1_hashed.version,
        policy_hash=policy_v1_hashed.document_hash,
        parsed_claims=[
            _parsed("claim-a"),
            _parsed("claim-b"),
            _parsed("claim-c"),
        ],
        decision=ConsentDecision.ACCEPTED,
        accepted_at="2026-04-01T10:00:00Z",
        valid_until="on_version_bump",
    )


@pytest.fixture
def conditional_record(policy_v1_hashed: PolicyDocument) -> ConsentRecord:
    """A conditional record disputing claim-b."""
    return ConsentRecord(
        record_id="rec-conditional",
        prev_record_id=None,
        caller_agent_id=CALLER,
        callee_agent_id=CALLEE,
        policy_version=policy_v1_hashed.version,
        policy_hash=policy_v1_hashed.document_hash,
        parsed_claims=[
            _parsed("claim-a"),
            _parsed("claim-b", disputed=True),
            _parsed("claim-c"),
        ],
        decision=ConsentDecision.CONDITIONAL,
        accepted_at="2026-04-01T10:00:00Z",
        valid_until="on_version_bump",
    )


def make_event(
    event_id: str,
    *,
    prev: str | None,
    consent_record_id: str,
    claim_id: str,
    decision: AdherenceDecision,
) -> AdherenceEvent:
    return AdherenceEvent(
        event_id=event_id,
        prev_event_id=prev,
        consent_record_id=consent_record_id,
        action="odrl:aggregate",
        clause_evaluated="§a",
        claim_id=claim_id,
        decision=decision,
        reasoning="test fixture",
        timestamp="2026-04-01T10:05:00Z",
    )
