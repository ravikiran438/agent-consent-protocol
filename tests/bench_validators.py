# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Micro-benchmark of the reference validators.

Measures the wall-clock cost of the three operations that a caller or
callee performs on every ACAP interaction:

    1. compute_policy_hash(policy)       , §3.1 content-addressing
    2. validate_consent_chain(chain)     , §3.2 structural invariant
    3. validate_adherence_trail(trail)   , §3.3-§3.4 chain integrity

The goal is to characterise per-call overhead on commodity hardware so
that implementers can reason about whether the protocol adds meaningful
latency compared to the network round-trip of a skill invocation itself
(typically tens of milliseconds).
"""

from __future__ import annotations

import statistics
import timeit

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
from acap.validators import (
    compute_policy_hash,
    validate_adherence_trail,
    validate_consent_chain,
)


def make_policy(num_claims: int) -> PolicyDocument:
    claims = [
        PolicyClaim(
            claim_id=f"claim-{i:04d}",
            clause_ref=f"§{i}",
            action="odrl:aggregate",
            asset="pii:session_data",
            rule_type=RuleType.PROHIBITION,
            constraint="odrl:purpose isNot behavioral_profiling",
            effective_version="1.0.0",
        )
        for i in range(num_claims)
    ]
    return PolicyDocument(
        version="1.0.0",
        document_uri="https://example.com/policy.json",
        document_hash="sha256:placeholder",
        effective_date="2026-04-01T00:00:00Z",
        claims=claims,
        publisher="https://example.com/agent",
        natural_language_uri="https://example.com/terms",
    )


def make_consent_chain(policy: PolicyDocument, chain_length: int) -> list[ConsentRecord]:
    policy_hash = compute_policy_hash(policy)
    parsed = [
        ParsedClaim(claim_id=c.claim_id, understood=True, disputed=False)
        for c in policy.claims
    ]
    records: list[ConsentRecord] = []
    prev_id: str | None = None
    for i in range(chain_length):
        rec = ConsentRecord(
            record_id=f"rec-{i:04d}",
            prev_record_id=prev_id,
            caller_agent_id="did:agent:caller",
            callee_agent_id="https://callee.example.com",
            policy_version=policy.version,
            policy_hash=policy_hash,
            parsed_claims=parsed,
            decision=ConsentDecision.ACCEPTED,
            accepted_at=f"2026-04-01T10:{i % 60:02d}:00Z",
            valid_until="on_version_bump",
        )
        records.append(rec)
        prev_id = rec.record_id
    return records


def make_trail(record: ConsentRecord, trail_length: int) -> list[AdherenceEvent]:
    events: list[AdherenceEvent] = []
    prev: str | None = None
    for i in range(trail_length):
        evt = AdherenceEvent(
            event_id=f"evt-{i:05d}",
            prev_event_id=prev,
            consent_record_id=record.record_id,
            action="odrl:aggregate",
            clause_evaluated="§0",
            claim_id=record.parsed_claims[i % len(record.parsed_claims)].claim_id,
            decision=AdherenceDecision.PERMIT,
            reasoning="benchmark run",
            timestamp=f"2026-04-01T10:{i % 60:02d}:00Z",
        )
        events.append(evt)
        prev = evt.event_id
    return events


def bench(fn, iterations: int = 1000) -> tuple[float, float]:
    """Return (median microseconds, p99 microseconds)."""
    samples = [
        timeit.timeit(fn, number=1) * 1e6  # convert seconds to microseconds
        for _ in range(iterations)
    ]
    samples.sort()
    median = statistics.median(samples)
    p99 = samples[int(iterations * 0.99)]
    return median, p99


def main() -> None:
    print(f"{'Operation':<45} {'median':>10} {'p99':>10}")
    print("-" * 67)

    # 1. Hash computation: 10 claims (typical), 50 claims (dense), 200 (large)
    for n in (10, 50, 200):
        policy = make_policy(n)
        med, p99 = bench(lambda p=policy: compute_policy_hash(p), iterations=500)
        print(f"{'compute_policy_hash (' + str(n) + ' claims)':<45} {med:>8.1f}μs {p99:>8.1f}μs")

    # 2. Chain validation: 10-claim policy, chain length 1, 5, 20
    policy = make_policy(10)
    policies = {policy.version: policy}
    for k in (1, 5, 20):
        chain = make_consent_chain(policy, k)
        med, p99 = bench(
            lambda c=chain: validate_consent_chain(c, policy_by_version=policies),
            iterations=500,
        )
        print(f"{'validate_consent_chain (len ' + str(k) + ')':<45} {med:>8.1f}μs {p99:>8.1f}μs")

    # 3. Trail validation: trail length 10, 100, 1000
    policy = make_policy(10)
    record = make_consent_chain(policy, 1)[0]
    records = {record.record_id: record}
    for m in (10, 100, 1000):
        trail = make_trail(record, m)
        med, p99 = bench(
            lambda t=trail: validate_adherence_trail(t, records),
            iterations=200 if m <= 100 else 50,
        )
        print(f"{'validate_adherence_trail (len ' + str(m) + ')':<45} {med:>8.1f}μs {p99:>8.1f}μs")


if __name__ == "__main__":
    main()
