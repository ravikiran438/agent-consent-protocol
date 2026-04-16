# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for acap.validators.chain."""

from __future__ import annotations

import pytest

from acap.types import ConsentDecision, ParsedClaim
from acap.validators.chain import (
    ChainValidationError,
    validate_consent_chain,
    validate_consent_record,
)
from acap.validators.hash import compute_policy_hash


def test_single_record_ok(first_record, policy_v1_hashed):
    # happy path: the record matches the policy and has full claim coverage
    validate_consent_record(first_record, policy=policy_v1_hashed)


def test_missing_parsed_claim_is_rejected(first_record, policy_v1_hashed):
    # drop claim-b from parsed_claims, this is the §3.2 invariant violation
    first_record.parsed_claims = [
        p for p in first_record.parsed_claims if p.claim_id != "claim-b"
    ]
    with pytest.raises(ChainValidationError, match="claim-b"):
        validate_consent_record(first_record, policy=policy_v1_hashed)


def test_extra_parsed_claim_is_rejected(first_record, policy_v1_hashed):
    # a ParsedClaim that doesn't exist in the PolicyDocument is suspicious
    first_record.parsed_claims.append(
        ParsedClaim(
            claim_id="claim-phantom",
            understood=True,
            disputed=False,
        )
    )
    with pytest.raises(ChainValidationError, match="claim-phantom"):
        validate_consent_record(first_record, policy=policy_v1_hashed)


def test_hash_mismatch_is_rejected(first_record, policy_v1_hashed):
    first_record.policy_hash = "sha256:" + "0" * 64
    with pytest.raises(ChainValidationError, match="policy_hash"):
        validate_consent_record(first_record, policy=policy_v1_hashed)


def test_version_mismatch_is_rejected(first_record, policy_v1_hashed):
    first_record.policy_version = "9.9.9"
    with pytest.raises(ChainValidationError, match="policy_version"):
        validate_consent_record(first_record, policy=policy_v1_hashed)


def test_conditional_without_dispute_is_rejected(first_record, policy_v1_hashed):
    """A conditional record with no disputed claims is malformed.

    The point of 'conditional' is to carry at least one dispute. An agent
    that accepts everything should use 'accepted', otherwise the callee
    can't tell what to gate.
    """
    first_record.decision = ConsentDecision.CONDITIONAL
    # all claims still undisputed
    with pytest.raises(ChainValidationError, match="disputed"):
        validate_consent_record(first_record, policy=policy_v1_hashed)


def test_conditional_with_dispute_is_ok(conditional_record, policy_v1_hashed):
    validate_consent_record(conditional_record, policy=policy_v1_hashed)


def test_empty_chain_rejected():
    with pytest.raises(ChainValidationError, match="empty"):
        validate_consent_chain([])


def test_chain_first_record_must_have_no_prev(first_record):
    first_record.prev_record_id = "rec-0"
    with pytest.raises(ChainValidationError, match="prev_record_id"):
        validate_consent_chain([first_record])


def test_chain_link_integrity(first_record, policy_v1_hashed):
    # build a second record that correctly links to the first
    second = first_record.model_copy(deep=True)
    second.record_id = "rec-2"
    second.prev_record_id = first_record.record_id
    second.policy_version = "2.0.0"

    # and a v2 policy for it to reference
    policy_v2 = policy_v1_hashed.model_copy(deep=True)
    policy_v2.version = "2.0.0"
    policy_v2.document_hash = compute_policy_hash(policy_v2)
    second.policy_hash = policy_v2.document_hash

    policies = {
        policy_v1_hashed.version: policy_v1_hashed,
        policy_v2.version: policy_v2,
    }
    validate_consent_chain([first_record, second], policy_by_version=policies)


def test_chain_broken_link_rejected(first_record):
    second = first_record.model_copy(deep=True)
    second.record_id = "rec-2"
    second.prev_record_id = "rec-not-real"

    with pytest.raises(ChainValidationError, match="prev_record_id"):
        validate_consent_chain([first_record, second])


def test_chain_mixed_pairs_rejected(first_record):
    """All records in a chain must share the same caller/callee."""
    second = first_record.model_copy(deep=True)
    second.record_id = "rec-2"
    second.prev_record_id = first_record.record_id
    second.callee_agent_id = "https://different-callee.example.com"

    with pytest.raises(ChainValidationError, match="different"):
        validate_consent_chain([first_record, second])


def test_chain_missing_policy_for_version_rejected(first_record):
    # caller asked for per-record policy verification but didn't supply v1
    with pytest.raises(ChainValidationError, match="no matching PolicyDocument"):
        validate_consent_chain([first_record], policy_by_version={})
