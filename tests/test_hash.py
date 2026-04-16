# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for acap.validators.hash."""

from __future__ import annotations

import copy

import pytest

from acap.validators.hash import (
    HASH_PREFIX,
    canonicalize,
    compute_policy_hash,
    verify_policy_hash,
)


def test_hash_has_prefix(policy_v1):
    h = compute_policy_hash(policy_v1)
    assert h.startswith(HASH_PREFIX)
    # sha256 hex is 64 chars
    assert len(h) == len(HASH_PREFIX) + 64


def test_hash_is_stable(policy_v1):
    """Hashing the same document twice yields the same digest."""
    assert compute_policy_hash(policy_v1) == compute_policy_hash(policy_v1)


def test_hash_ignores_document_hash_field(policy_v1):
    """The document_hash field is zeroed before hashing, per §3.1.

    Otherwise the hash would depend on what's already in the field,
    making the canonical hash impossible to compute.
    """
    h1 = compute_policy_hash(policy_v1)

    doc2 = policy_v1.model_copy()
    doc2.document_hash = "sha256:deadbeef" * 8
    h2 = compute_policy_hash(doc2)

    assert h1 == h2


def test_hash_changes_on_claim_edit(policy_v1):
    """A meaningful change to any claim flips the hash."""
    before = compute_policy_hash(policy_v1)

    tampered = policy_v1.model_copy(deep=True)
    tampered.claims[0].constraint = "odrl:purpose is marketing"

    after = compute_policy_hash(tampered)
    assert before != after


def test_hash_changes_on_claim_reorder(policy_v1):
    """Claim order matters (§3.1: 'claim order is significant')."""
    before = compute_policy_hash(policy_v1)

    shuffled = policy_v1.model_copy(deep=True)
    shuffled.claims = list(reversed(shuffled.claims))

    after = compute_policy_hash(shuffled)
    assert before != after


def test_verify_accepts_prefixed_and_bare(policy_v1):
    h = compute_policy_hash(policy_v1)
    bare = h[len(HASH_PREFIX):]

    assert verify_policy_hash(policy_v1, h)
    assert verify_policy_hash(policy_v1, bare)


def test_verify_rejects_empty_hash(policy_v1):
    assert not verify_policy_hash(policy_v1, "")


def test_verify_rejects_wrong_hash(policy_v1):
    assert not verify_policy_hash(policy_v1, f"{HASH_PREFIX}{'0' * 64}")


def test_canonicalize_sorts_keys():
    out = canonicalize({"b": 1, "a": 2, "c": 3})
    assert out == b'{"a":2,"b":1,"c":3}'


def test_canonicalize_rejects_nan():
    with pytest.raises(ValueError):
        canonicalize({"x": float("nan")})


def test_canonicalize_handles_nested(policy_v1):
    """Round-trip a realistic nested structure."""
    dumped = policy_v1.model_dump(mode="json", exclude_none=True)
    out = canonicalize(dumped)
    # can be re-parsed
    import json as _json
    parsed = _json.loads(out)
    assert parsed["version"] == "1.0.0"
    assert len(parsed["claims"]) == 3
