# Audit Projection: Status

**Stage:** Design proposal
**Specification:** Not yet drafted
**Implementation:** Not yet started
**Depends on:** Anumati Core v0.1+

## What exists

- High-level framing of the three report sections in `README.md`
- Informal example of an executive summary paragraph

## What's open

- Protobuf schema for `AuditReport`, `AuditEntry`, `ClaimAuditSummary`,
  `VersionAuditSummary`
- Template / rendering choices for the natural-language layer
- Interaction with the `governance-tiering` extension: how are
  `EscalationAssessment` records surfaced in the report?
- Interaction with the `regulatory-context` extension: does the report
  carry a regulatory-obligation section?

## Not in scope

- Real-time dashboards (this is a point-in-time projection)
- Cross-caller aggregate reports (one caller-callee pair per report)
