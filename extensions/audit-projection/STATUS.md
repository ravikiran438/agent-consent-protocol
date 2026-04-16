# Audit Projection: Status

**Stage:** Design proposal
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/audit-projection/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

This extension defines how the machine-readable ACAP consent chain and
adherence trail are projected into human-readable audit artefacts for
compliance officers, legal teams, regulators, and principals. The
projection is lossless with respect to the underlying signed records:
every narrative assertion carries a back-reference to the
`ConsentRecord` or `AdherenceEvent` it summarises, so an auditor who
doubts the narrative can always resolve to the canonical record.

## Primitives this extension adds

- `AuditReport`, the top-level projection for a caller-callee pair
  over a stated time window
- `AuditEntry`, an individual timestamped narrative entry rendered
  from one `ConsentRecord` or one `AdherenceEvent`
- `ClaimAuditSummary`, per-claim statistical breakdown (evaluations,
  permits, denies, escalations) over the window
- `VersionAuditSummary`, per-policy-version summary with active-dates
  and event counts
- `GenerateAuditReport`, the RPC that walks the chain and trail for a
  given (caller, callee, window) triple and returns the projection

The intended regulatory touchpoints are the GDPR Recital 71 and
Art. 13(2)(f) / 14(2)(g) expectations for automated-decision-making
disclosures, and the EU AI Act Annex IV technical-documentation
requirements for high-risk deployments.

## Interop points with ACAP Core

- Input: the full `ConsentRecord` chain for a (caller, callee) pair,
  plus the full `AdherenceEvent` trail for each `ConsentRecord` in
  that chain
- Output: a single `AuditReport` object; no new state is written back
  to Core records
- The projection is deterministic: given the same inputs and the same
  rendering template, two implementations MUST produce byte-identical
  executive summaries and statistical sections. Narrative entries MAY
  differ in prose style but MUST carry the same `event_id` references.

## What exists today

- High-level framing of the three report sections (executive summary,
  chronological timeline, per-claim and per-version summaries) in
  `README.md`
- Informal example of an executive summary paragraph

## What is open

- Protobuf schema for `AuditReport`, `AuditEntry`, `ClaimAuditSummary`,
  `VersionAuditSummary`, `GenerateAuditReport`
- Rendering template specification for the natural-language layer
- Interaction with the `governance-tiering` extension: how are
  `EscalationAssessment` records surfaced in the report?
- Interaction with the `regulatory-context` extension: does the report
  carry a per-obligation compliance section?

## Not in scope

- Real-time dashboards (this is a point-in-time projection)
- Cross-caller aggregate reports (one caller-callee pair per report)
- Enforcement actions based on report content (reports are
  informational; any automation built on them is a separate concern)

## Feedback

Open an issue or a PR on the parent repository. Reference this
extension in the title: `[audit-projection] <your topic>`.
