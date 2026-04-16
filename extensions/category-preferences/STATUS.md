# Category Preferences: Status

**Stage:** Design proposal
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/category-preferences/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

This extension defines how a human principal expresses **asymmetric
sensitivity** over the data the calling agent may encounter, across
two orthogonal axes: the category of data (biometric, health,
financial, and so on) and the dimension of use (storage, access,
third-party sharing, training, and so on). The result is a two-axis
matrix that travels with the `ConsentRecord` per-callee, replacing the
single "I agree" flag with a grid that a caller-side evaluator can
consult before each action.

## Primitives this extension adds

- `CategoryPreference`, a map keyed by (`Category`, `Dimension`) with
  `SensitivityLevel` values
- `Category`, an enum of nine values: biometric, health, financial,
  location, behavioural, identity, communications, minor-or-dependent,
  operational
- `Dimension`, an enum of eight values: storage, access,
  third-party-sharing, automated-decision, training, aggregation,
  cross-context-use, deletion-or-portability
- `SensitivityLevel`, a three-value enum: `LOW`, `MEDIUM`, `HIGH`
- `sensitivity_override_justification`, a free-text field when a
  caller evaluates an action against a non-default cell

The matrix is declarative rather than inferred: the principal states
the cells, they are not learned from past behaviour. A `HIGH`
sensitivity on a cell does not by itself imply HIPAA or GDPR
compliance; regulatory-framework floors are the concern of the
`regulatory-context` extension, which consumes the same grid as its
encoding surface.

## Interop points with ACAP Core

- `ConsentRecord.category_preferences` (new optional field) carries
  the grid declared at bind time
- At evaluation time, a caller-side evaluator consults the cell
  matching the `(PolicyClaim.asset, PolicyClaim.action)` pair and
  records the consulted cell in the `AdherenceEvent.context`
- The `regulatory-context` extension uses the same (category,
  dimension) grid as the encoding surface for regulatory obligation
  floors; `effective_sensitivity` is the max across principal,
  callee, and regulatory declarations

## What exists today

- Vocabulary proposal in `README.md` (9 categories, 8 dimensions)
- Default and override semantics sketch
- Worked example showing the same principal at a surgery app versus a
  pharmacy

## What is open

- Protobuf schema for `CategoryPreference` and the enums
- User study validating the two-axis model (does a human actually find
  the 9x8 grid usable, and are there common cells that should be
  collapsed or split?)
- Interaction with the `governance-tiering` extension: how does a
  `HIGH` cell feed into the materiality assessment on a policy version
  bump?
- How far should the vocabularies be normalised vs left to deployment
  conventions?

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
