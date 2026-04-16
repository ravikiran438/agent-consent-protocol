# ADR 002: Proof of Adherence Over Proof of Acceptance

**Status:** Accepted
**Date:** 2026-03-03
**Authors:** ACAP Working Group

---

## Context

Traditional consent systems, designed for humans, produce *proof of
acceptance*: a timestamp, an identity record, and a version identifier
proving that a party clicked "I agree" to a document at a point in time.
This model has two structural weaknesses:

1. **Understanding is assumed.** The accepting party is not required to
   demonstrate any comprehension of the terms. Acceptance is binary.
2. **Subsequent compliance is unverifiable.** There is no mechanism to prove
   that the accepting party actually honoured the terms after acceptance.

AI agents are structurally different from humans in both respects. An agent:

- *Can* parse every clause of a policy document.
- *Can* evaluate a policy clause before every action.
- *Can* produce a natural-language justification for its evaluation.
- *Cannot* "blindly click" in the way humans routinely do.

Three consent models were considered for ACAP:

1. **Proof of acceptance (human model):** Record that the agent accepted the
   document version. No per-action auditing.
2. **Scope-based gating:** Map policy rules to OAuth scopes; gate skill
   invocation on scope possession.
3. **Proof of adherence:** Record acceptance AND a per-action reasoning
   record referencing the specific clause evaluated.

## Decision

ACAP implements *proof of adherence*: calling agents MUST record a
`ParsedClaim` for every `PolicyClaim` in the `PolicyDocument` (establishing
comprehension), and SHOULD record an `AdherenceEvent` for every action
attempted (establishing per-action compliance).

## Rationale

**Against option 1 (acceptance only):** Produces no evidence of comprehension
or subsequent compliance. Provides no more accountability than a human
click-through. Does not exploit the unique capability of agents to reason
about policy text.

**Against option 2 (scope-based gating):** OAuth scopes are discrete,
static, and binary. Usage policy is contextual, evolving, and semantic. The
constraint `"odrl:purpose isNot behavioral_profiling"` cannot be encoded in
a scope. A scope-only system requires policy authors to reduce their legal
text to flat permission lists, losing the nuance that makes policies legally
meaningful.

**For option 3 (proof of adherence):**

- `ParsedClaim` establishes that the agent processed every clause. An agent
  that records `understood: true` for a prohibition and then violates it has
  demonstrably acted in bad faith, a higher standard of liability than a
  human who clicked without reading.
- `AdherenceEvent.reasoning` is the mechanism that makes agent behaviour
  auditable at the action level. It is the ACAP equivalent of a decision log
  in a rules engine.
- The `claim_id` + `clause_ref` fields in `AdherenceEvent` provide
  fine-grained citation: auditors can trace any enforcement decision back to
  the exact clause that governed it.
- The linked-list structure of both chains (`prev_record_id`,
  `prev_event_id`) ensures that no record can be silently removed or
  reordered without breaking the chain.

## Linked List Provenance

The singly-linked consent chain structure is derived from a production
human-auth system that preserved all accepted versions of Terms of Service
per user as a legal audit trail (prior art, 2019–2022). ACAP adapts this
pattern to the agent context and extends it to per-action adherence events,
which have no equivalent in the human system (because humans cannot produce
per-action policy justifications at scale).

## Consequences

- Calling agents take on a non-trivial implementation burden: they must
  parse `PolicyClaim` objects and reason about them at runtime.
- The `reasoning` field on `AdherenceEvent` is free-form text. A future ACAP
  version MAY define a structured reasoning format; for v0.1 natural language
  is sufficient and more auditor-friendly.
- An agent that records `understood: false` for a claim signals to the
  callee that the policy language is ambiguous. Callee policy authors SHOULD
  monitor disputed and not-understood claims to improve policy clarity.
- The `escalate_on_deny` field on `PolicyClaim` allows policy authors to
  mark high-stakes prohibitions that require human-in-the-loop review on
  violation, bridging the gap between autonomous agent operation and
  mandatory human oversight.
