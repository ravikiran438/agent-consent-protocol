# Governance Tiering: Status

**Stage:** Design proposal
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/governance-tiering/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

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
- Draft of the five materiality criteria
- Informal exploration of auto / reviewed / required tier classification

## What is open

- Formal TLA+ specification of the escalation state machine
- Protobuf schema for `EscalationAssessment`, `MaterialitySignal`,
  `EscalationTier`, `DelegationChain`
- Reference implementation of a governance-agent SDK
- Empirical evaluation: does tiering actually reduce alert fatigue in
  a pilot deployment?

## Not in scope

- Cross-agent reputation systems
- Economic models for governance-agent incentives
- Regulatory certification of governance-agent behaviour

These are worth exploring separately once the mechanics are settled.

## Feedback

Open an issue or a PR on the parent repository. Reference this
extension in the title: `[governance-tiering] <your topic>`.
