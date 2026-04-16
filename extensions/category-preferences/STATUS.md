# Category Preferences: Status

**Stage:** Design proposal
**Specification:** Not yet drafted
**Implementation:** Not yet started
**Depends on:** Anumati Core v0.1+

## What exists

- Vocabulary proposal in `README.md` (9 categories, 8 dimensions)
- Default / override semantics sketch
- Worked example showing same principal at surgeon vs. pharmacy

## What's open

- Protobuf schema for the `category_preferences` map
- User study validating the two-axis model
- Interaction with the `governance-tiering` extension: how does a
  `HIGH`-cell flag feed into the materiality assessment?
- How far should the vocabularies be normalised vs. left to deployments?

## Not in scope

- Machine-learned preference inference
- Cross-principal preference aggregation
- Enforcement of preferences by the callee (this is a caller-side
  signalling mechanism)
