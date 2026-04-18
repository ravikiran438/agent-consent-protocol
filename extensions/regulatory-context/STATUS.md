# Regulatory Context: Status

**Stage:** Reference implementation (envelope only); per-framework mappings blocked on qualified legal review
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/regulatory-context/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+, Category Preferences Extension (for the obligation-encoding grid)
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

See `motivation.md` for the problem framing, the alternatives
considered, and the design rationale. What follows is the engineering
summary.

This extension defines the machine-readable envelope by which
jurisdictional regulatory obligations
([HIPAA](https://www.hhs.gov/hipaa/index.html),
[GDPR](https://gdpr-info.eu/),
[PCI-DSS](https://www.pcisecuritystandards.org/),
[CCPA](https://oag.ca.gov/privacy/ccpa),
[EU AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai),
[COPPA](https://www.ftc.gov/legal-library/browse/rules/childrens-online-privacy-protection-rule-coppa),
sector-specific frameworks) travel through the ACAP consent chain
as floors that neither the callee's policy claims nor the principal's
preferences can lower. It is the mechanism by which
each industry's existing consent playbook plugs into ACAP without
ACAP itself encoding the legal content of those playbooks.

## Primitives this extension adds

- `RegulatoryContext`, a field on both `PolicyDocument` (callee's
  declared compliance context) and `ConsentRecord` (caller's declared
  compliance context)
- `ComplianceObligation`, a structured constraint consisting of
  (framework, article, category, dimension, minimum sensitivity level)
- `RegulatoryFramework`, a closed enum of eight values: GDPR, HIPAA,
  PCI-DSS, CCPA, EU AI Act, COPPA, SOC2, FINRA
- `role`, a free-form string declaring the declaring party's position
  under the framework (data controller, data processor, covered entity,
  business associate, merchant, deployer, provider); kept as a string
  until a working group stabilizes a closed vocabulary
- `compute_floor`, the strictest-across-sources computation that
  returns the effective sensitivity for a (category, dimension) query

The intended industry-specific playbooks this envelope is designed to
carry include HIPAA authorizations,
[GDPR Art. 6](https://gdpr-info.eu/art-6-gdpr/) /
[Art. 9](https://gdpr-info.eu/art-9-gdpr/) lawful bases, PCI-DSS
cardholder-data rules, CCPA categories,
[EU AI Act Article 50](https://artificialintelligenceact.eu/article/50/)
deployer obligations,
[42 CFR Part 2](https://www.ecfr.gov/current/title-42/chapter-I/subchapter-A/part-2),
COPPA verifiable parental consent, and
[MiFID II](https://eur-lex.europa.eu/eli/dir/2014/65/oj) client
categorization. ACAP provides the
structure; the legal content of each framework mapping is supplied by
qualified domain specialists, not by the protocol.

## Interop points with ACAP Core

- `PolicyDocument.regulatory_contexts` (carried as extension envelope
  data; no Core schema change required)
- `ConsentRecord.regulatory_contexts` (carried the same way)
- At evaluation time, an `AdherenceEvent` MUST honor the strictest
  floor across all declared contexts before permitting an action; the
  reference `compute_floor` function implements this rule against the
  category-preferences grid
- The `category-preferences` extension's (category, dimension) grid is
  the encoding surface for obligation cells

## What exists today

- Design sketch in `README.md` and full rationale in `motivation.md`
- Protobuf schema for `RegulatoryContext`, `ComplianceObligation`,
  and `RegulatoryFramework` in `consent.regulatory.proto`
- Python reference types (`types.py`), mirroring the proto
- Reference floor computation (`floor.py`) using the LOW < MEDIUM <
  HIGH lattice and composing principal preference with an arbitrary
  number of declared regulatory contexts
- Structural validator (`validator.py`) enforcing non-empty roles and
  unique obligation references; the validator makes NO claim about
  whether a declared context accurately represents the named
  regulation
- Test suite (16 tests under `tests/extensions/test_regulatory_context.py`)
  using HYPOTHETICAL framework-agnostic obligations so the tests
  cannot be mis-read as a normative mapping of any real regulation

## What is open

- Legal review of candidate HIPAA / GDPR / PCI-DSS / EU AI Act
  mappings before any of them are published as reference material
- A working group to maintain obligation libraries as regulations
  change
- AgentCard advertisement convention for how a caller announces that
  it honors a floor, and how obligation references are dereferenced
  out-of-band
- A closed vocabulary for the `role` field once a regulatory working
  group stabilizes one
- Interaction with the `audit-projection` extension: per-obligation
  compliance summaries in the regulator-facing report

## What will NOT ship without qualified review

- Any normative mapping of a specific regulatory article to a
  (category, dimension, sensitivity) tuple
- Any claim that a deployment carrying a given `RegulatoryContext`
  satisfies the named regulation
- Any claim of endorsement by a regulator, bar association, or
  standards body

The protocol can provide the structure to carry such mappings without
making the mappings themselves part of the spec. That is the boundary
this extension proposes to draw.

## Seeking collaborators

If you are a compliance engineer, data-protection lawyer, healthcare
regulatory specialist, PCI-QSA, or have worked on EU AI Act deployer
obligations, and would be interested in co-maintaining the mapping
library for one framework, please open an issue on the parent
repository.

## Feedback

Open an issue or a PR on the parent repository. Reference this
extension in the title: `[regulatory-context] <your topic>`.
