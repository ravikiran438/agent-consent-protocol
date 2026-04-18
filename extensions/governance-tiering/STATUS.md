# Governance Tiering: Status

**Stage:** Reference implementation
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/governance-tiering/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

See `motivation.md` for the problem framing, the alternatives
considered, and the design rationale. What follows is the engineering
summary.

This extension defines how policy-version bumps in ACAP are tiered by
materiality so that immaterial changes (typos, clause renumbering,
constraint tightenings) do not interrupt the human principal, while
material changes (new claims, removed permissions, `rule_type` inversions)
are escalated with an auditable delegation record. The extension
introduces a `governance_agent` as an optional supervisory party whose
classification decisions are themselves recorded in the consent chain.

## Primitives this extension adds

- `EscalationAssessment`, an object attached to a `ConsentRecord`
  describing the governance agent's classification of a version bump
- `MaterialitySignal`, the structured evidence used to classify
  (new claim, removed permission, `rule_type` change, `escalate_on_deny`
  flag, caller-capability change)
- `EscalationTier`, an enum with three values: `AUTO_APPROVED`,
  `GOVERNANCE_REVIEWED`, `HUMAN_REQUIRED`
- `DelegationChain`, an extension to the consent chain for
  Agent A → Agent B → Agent C paths where each hop may be tiered
  independently

## Interop points with ACAP Core

- `ConsentRecord.escalation` (new optional field) carries the
  `EscalationAssessment` when a governance agent was involved
- `PolicyDocument.claim.escalate_on_deny` (existing Core field) feeds
  directly into `MaterialitySignal`
- The tiered classification does not alter the Core chain-integrity
  invariants; a governance-tiered `ConsentRecord` is still a
  Core-conformant record that Core validators can check

## What exists today

- Design sketch in `README.md`
- TLA+ specification of the escalation state machine, invariants S8
  (`GovernanceAlwaysReviews`) and S9 (`HumanRequiredHonoured`), in
  `specification/ConsentLifecycle.tla` at the repository root (modelled
  jointly with Core because the tiered flow adds a `GovernanceReview`
  state)
- Protobuf schema for `ClaimDiff`, `PolicyDiff`, `EscalationTier`,
  `MaterialitySignal`, `EscalationAssessment`, `DelegationHop`, and
  `DelegationChain` in `consent.governance.proto`
- Python reference types (`types.py`), mirroring the proto
- Reference governance-agent SDK (`materiality.py`) with six structural
  signals: `new_claim`, `removed_claim`, `modified_claim`,
  `rule_type_inversion`, `constraint_relaxed`, `escalate_on_deny_added`.
  The tier mapping is hardcoded in the reference: the last four force
  `HUMAN_REQUIRED`, `new_claim` and `modified_claim` force at least
  `GOVERNANCE_REVIEWED`. Downstream agents that want a different policy
  override `classify` rather than configuring this one.
- Runtime validators (`validator.py`) for `EscalationAssessment` (checks
  the S9 human-review invariant) and `DelegationChain` (checks
  contiguity and origin anchoring)
- Test suite (24 tests under `tests/extensions/test_governance_tiering.py`)
  covering diff computation, classifier tier selection, and validator
  invariants

## What is open

- AgentCard advertisement convention for governance-agent endpoints,
  how a caller discovers and authenticates a governance agent
- LLM-assisted semantic classifier that can judge "relaxed vs
  tightened" constraints beyond the current length heuristic
- Empirical evaluation: does tiering actually reduce alert fatigue in
  a pilot deployment?
- Graduation of S8 and S9 into a standalone TLA+ module once the
  extension is adopted by a second implementation

## Not in scope

- Cross-agent reputation systems
- Economic models for governance-agent incentives
- Regulatory certification of governance-agent behaviour

These are worth exploring separately once the mechanics are settled.

## Feedback

Open an issue or a PR on the parent repository. Reference this
extension in the title: `[governance-tiering] <your topic>`.
