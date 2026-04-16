# Governance Tiering: Status

**Stage:** Design proposal
**Specification:** Not yet drafted
**Implementation:** Not yet started
**Depends on:** Anumati Core v0.1+

## What exists

- Design sketch in `README.md`
- Informal exploration of the auto/reviewed/required tier classification
- Draft of the materiality criteria (new claim, removed permission,
  `rule_type` change, `escalate_on_deny` flag, capability change)

## What's open

- Formal TLA+ specification of the escalation state machine
  (properties analogous to S7–S9 in Core)
- Protobuf schema for `EscalationAssessment`, `MaterialitySignal`,
  and the three tier values
- Reference implementation of a governance-agent SDK
- Evaluation: does tiering actually reduce alert fatigue in practice?
  (would need a pilot with a deploying org)

## Not in scope

- Cross-agent reputation systems
- Economic models for governance-agent incentives
- Regulatory certification of governance-agent behaviour

These are worth exploring separately once the mechanics are settled.

## Feedback

Open an issue or a PR on the parent repository. Reference this extension
in the title: `[governance-tiering] <your topic>`.
