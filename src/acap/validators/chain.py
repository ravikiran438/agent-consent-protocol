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

"""Consent chain validator.

Walks a sequence of ConsentRecord entries and checks the structural
invariants from Anumati §3.2:

  1. The first record has prev_record_id == None; every subsequent
     record's prev_record_id points to the previous record's id.
  2. All records share the same (caller_agent_id, callee_agent_id)
     pair, a chain is per-pair.
  3. Every PolicyClaim in the referenced PolicyDocument has a matching
     ParsedClaim in the ConsentRecord. This is the "critical invariant"
     from §3.2, agents can't silently skip inconvenient clauses.
  4. When a PolicyDocument is provided, the record's policy_hash matches
     the document's hash (tamper evidence).

Signatures (JWS) are not verified here. That's a separate concern and
requires the caller's public key; see §6.1 on the threat model.
"""

from __future__ import annotations

from typing import Optional

from acap.types import ConsentRecord, PolicyDocument
from acap.validators.hash import compute_policy_hash


class ChainValidationError(ValueError):
    """Raised when a consent chain fails structural validation."""


def validate_consent_record(
    record: ConsentRecord,
    policy: Optional[PolicyDocument] = None,
) -> None:
    """Validate a single ConsentRecord.

    If ``policy`` is given, we also check claim coverage and hash match.
    Raises ChainValidationError on failure.
    """
    # Every claim needs a parsed counterpart, this is the invariant
    # that distinguishes proof-of-adherence from a boolean accept.
    if policy is not None:
        policy_claim_ids = {c.claim_id for c in policy.claims}
        parsed_claim_ids = {p.claim_id for p in record.parsed_claims}

        missing = policy_claim_ids - parsed_claim_ids
        if missing:
            raise ChainValidationError(
                f"ConsentRecord {record.record_id} is missing ParsedClaim "
                f"entries for: {sorted(missing)}"
            )

        extra = parsed_claim_ids - policy_claim_ids
        if extra:
            raise ChainValidationError(
                f"ConsentRecord {record.record_id} has ParsedClaim entries "
                f"not in PolicyDocument {policy.version}: {sorted(extra)}"
            )

        # Hash match, guards against a record that was signed against
        # a different version of the document than the one we have.
        expected_hash = compute_policy_hash(policy)
        if record.policy_hash != expected_hash:
            raise ChainValidationError(
                f"ConsentRecord {record.record_id} policy_hash "
                f"{record.policy_hash!r} does not match computed hash "
                f"{expected_hash!r} for policy v{policy.version}"
            )

        if record.policy_version != policy.version:
            raise ChainValidationError(
                f"ConsentRecord {record.record_id} policy_version "
                f"{record.policy_version!r} does not match PolicyDocument "
                f"version {policy.version!r}"
            )

    # Conditional consent must carry at least one dispute, otherwise
    # the decision is effectively "accepted" and the caller should have
    # used that instead.
    if record.decision.value == "conditional":
        disputes = [p for p in record.parsed_claims if p.disputed]
        if not disputes:
            raise ChainValidationError(
                f"ConsentRecord {record.record_id} is conditional but "
                "contains no disputed ParsedClaims"
            )


def validate_consent_chain(
    chain: list[ConsentRecord],
    policy_by_version: Optional[dict[str, PolicyDocument]] = None,
) -> None:
    """Validate an ordered list of ConsentRecords.

    The list MUST be ordered oldest-first. Pass ``policy_by_version``
    if you want per-record claim/hash verification; otherwise we only
    check structural link integrity.

    Raises ChainValidationError on first failure encountered.
    """
    if not chain:
        raise ChainValidationError("consent chain is empty")

    first = chain[0]
    if first.prev_record_id is not None:
        raise ChainValidationError(
            f"first record {first.record_id} has prev_record_id "
            f"{first.prev_record_id!r}; expected None"
        )

    caller = first.caller_agent_id
    callee = first.callee_agent_id

    for i, rec in enumerate(chain):
        # Same pair across the chain.
        if rec.caller_agent_id != caller or rec.callee_agent_id != callee:
            raise ChainValidationError(
                f"record at index {i} ({rec.record_id}) has different "
                f"caller/callee than the chain "
                f"({rec.caller_agent_id} -> {rec.callee_agent_id} vs. "
                f"{caller} -> {callee})"
            )

        # Link integrity.
        if i > 0:
            prev = chain[i - 1]
            if rec.prev_record_id != prev.record_id:
                raise ChainValidationError(
                    f"record at index {i} ({rec.record_id}) has "
                    f"prev_record_id {rec.prev_record_id!r}; expected "
                    f"{prev.record_id!r}"
                )

        # Per-record checks (claim coverage, hash).
        policy = None
        if policy_by_version is not None:
            policy = policy_by_version.get(rec.policy_version)
            if policy is None:
                raise ChainValidationError(
                    f"record {rec.record_id} references policy version "
                    f"{rec.policy_version!r} but no matching PolicyDocument "
                    "was supplied"
                )
        validate_consent_record(rec, policy=policy)
