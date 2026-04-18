# Audit Projection: Status

**Stage:** Reference implementation
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/audit-projection/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

See `motivation.md` for the problem framing, the alternatives
considered, and the design rationale. What follows is the engineering
summary.

This extension defines how the machine-readable ACAP consent chain and
adherence trail are projected into human-readable audit artefacts for
compliance officers, legal teams, regulators, and principals. The
projection is lossless with respect to the underlying signed records:
every narrative assertion carries a back-reference to the
`ConsentRecord` or `AdherenceEvent` it summarizes, so an auditor who
doubts the narrative can always resolve to the canonical record.

## Primitives this extension adds

- `AuditReport`, the top-level projection for a caller-callee pair
  over a stated time window
- `AuditEntry`, an individual timestamped narrative entry rendered
  from one `ConsentRecord` or one `AdherenceEvent`, carrying a
  back-reference to the source record
- `AuditEntryType`, a closed enum of ten values covering initial and
  re-consent, the three adherence decisions, governance-tiering
  events (auto / reviewed / human review), and consent invalidation
- `ClaimAuditSummary`, per-claim statistical breakdown (total
  evaluations, permits, denies, escalations) over the window
- `VersionAuditSummary`, per-policy-version summary with
  active-dates and event counts
- `AuditReportRequest`, the scope specification (caller, callee, time
  window, policy-version filter, claim-id filter, decision filter)
- `generate_report`, the projection function that walks the Core
  chain and trail and returns an `AuditReport`

## Interop points with ACAP Core

- Input: the full `ConsentRecord` chain for a (caller, callee) pair,
  plus the full `AdherenceEvent` trail for each `ConsentRecord` in
  that chain; an optional `{policy_version: PolicyDocument}` dict for
  claim-metadata enrichment
- Output: a single `AuditReport` object; no new state is written back
  to Core records
- The projection is deterministic: given the same inputs and the same
  filters, two conformant implementations MUST produce byte-identical
  statistical sections (executive-summary counts, per-claim counts,
  per-version counts). Narrative prose MAY differ in style but MUST
  carry the same cross-references.

## What exists today

- Design sketch in `README.md` and full rationale in `motivation.md`
- Protobuf schema for `AuditReport`, `AuditEntry`, `AuditEntryType`,
  `ClaimAuditSummary`, `VersionAuditSummary`, and `AuditReportRequest`
  in `consent.audit.proto`
- Python reference types (`types.py`), mirroring the proto
- Reference projector (`projector.py`) that merges the consent chain
  and adherence trail into a chronological timeline, emits per-claim
  and per-version summaries, and applies time / version / claim /
  decision filters from the request
- Structural validator (`validator.py`) enforcing 1-based consecutive
  sequence indexing, chronological timeline order, presence of at
  least one back-reference on every entry, and per-claim count
  consistency between the timeline and the summaries
- Test suite (19 tests under `tests/extensions/test_audit_projection.py`)
  covering happy-path projection, every filter dimension, edge cases
  (empty chain, missing policies, cross-pair leakage), and the
  validator's four invariants

## What is open

- Rendering-template specification for the narrative layer (the
  reference implementation uses f-string templates; a downstream
  extension can add language-model-augmented rendering as long as the
  cross-references and counts remain byte-identical)
- Multi-language rendering. The `language` field is in the proto but
  the reference implementation supports English only
- Interaction with the `governance-tiering` extension: render
  `EscalationAssessment` entries as `GOVERNANCE_AUTO`,
  `GOVERNANCE_REVIEWED`, and `HUMAN_REVIEW` timeline entries (the
  enum values are reserved but not wired in the reference projector)
- Interaction with the `regulatory-context` extension: per-obligation
  compliance section in the report
- Report signing and storage conventions

## Not in scope

- Real-time dashboards (this is a point-in-time projection)
- Cross-caller aggregate reports (one caller-callee pair per report)
- Enforcement actions based on report content (reports are
  informational; any automation built on them is a separate concern)

## Feedback

Open an issue or a PR on the parent repository. Reference this
extension in the title: `[audit-projection] <your topic>`.
