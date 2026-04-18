# Category Preferences: Status

**Stage:** Reference implementation
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/category-preferences/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

See `motivation.md` for the problem framing, the alternatives
considered, and the design rationale. What follows is the engineering
summary.

This extension defines how a human principal expresses **asymmetric
sensitivity** over the data the calling agent may encounter, across
two orthogonal axes: the category of data (biometric, health,
financial, and so on) and the dimension of use (storage, access,
third-party sharing, training, and so on). The result is a two-axis
matrix that travels with the `ConsentRecord` per-callee, replacing the
single "I agree" flag with a grid that a caller-side evaluator can
consult before each action.

## Primitives this extension adds

- `CategoryPreference`, one cell of the matrix, mapping a
  `(DataCategory, UsageDimension)` pair to a `CategorySensitivity`
  value with an optional principal-authored note
- `DataCategory`, a closed enum of nine values: biometric, health,
  financial, location, behavioral, identity, communications,
  minor-or-dependent, operational
- `UsageDimension`, a closed enum of eight values: storage, access,
  third-party sharing, automated decision, training, aggregation,
  cross-context use, deletion or portability
- `CategorySensitivity`, a three-value enum: `LOW`, `MEDIUM`, `HIGH`
- `resolve_sensitivity`, the matrix lookup function with
  specific-cell-wins-over-default-row semantics and a `LOW` fallback
  on absence of opinion

The matrix is declarative rather than inferred: the principal states
the cells, they are not learned from past behavior. A `HIGH`
sensitivity on a cell does not by itself imply
[HIPAA](https://www.hhs.gov/hipaa/index.html) or
[GDPR](https://gdpr-info.eu/) compliance; regulatory-framework floors
are the concern of the `regulatory-context` extension, which consumes
the same grid as its encoding surface.

## Interop points with ACAP Core

- The preference list travels with the per-callee `ConsentRecord` as
  extension-envelope data; no Core schema change is required
- At evaluation time, a caller-side adapter maps the claim's `action`
  and `asset` to a `(category, dimension)` query and consults
  `resolve_sensitivity`; the consulted cell is recorded in the
  `AdherenceEvent.context` for audit
- The `regulatory-context` extension uses the same (category,
  dimension) grid as the encoding surface for regulatory obligation
  floors; the effective sensitivity is the strictest across principal,
  callee, and regulatory declarations

## What exists today

- Design sketch in `README.md` and full rationale in `motivation.md`
- Protobuf schema for `CategoryPreference`, `DataCategory` (9 values),
  `UsageDimension` (8 values), and `CategorySensitivity` (3 values) in
  `consent.categories.proto`
- Python reference types (`types.py`), mirroring the proto
- Reference resolver (`resolver.py`) with default-row fallback
- Runtime validator (`validator.py`) enforcing per-cell uniqueness
- Test suite (13 tests under `tests/extensions/test_category_preferences.py`)
  covering resolution semantics, the default-row override, the
  uniqueness invariant, and the two worked examples from the README

## What is open

- AgentCard advertisement convention for how a caller announces that
  it consults a matrix and how a principal's matrix is exchanged
- Reference mapping from [ODRL 2.2](https://www.w3.org/TR/odrl-model/)-aligned `action` and `asset` vocabularies
  to `(category, dimension)` queries; the mapping is currently the
  caller's job and different deployments will map differently
- User study validating that the 9x8 vocabulary is one a human can
  actually reason about, and whether common cells should be collapsed
  or split
- Interaction with the `governance-tiering` extension: a claim
  affecting a `HIGH` cell should be a candidate for automatic
  `HUMAN_REQUIRED` escalation regardless of structural signals on the
  policy diff

## Not in scope

- Machine-learned preference inference
- Cross-principal preference aggregation
- Enforcement of preferences by the callee (this is a caller-side
  signalling mechanism)
- Preference portability between callees (the matrix is per-callee by
  design, because context shifts meaning)

## Feedback

Open an issue or a PR on the parent repository. Reference this
extension in the title: `[category-preferences] <your topic>`.
