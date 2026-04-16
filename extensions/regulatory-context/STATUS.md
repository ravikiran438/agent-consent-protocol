# Regulatory Context: Status

**Stage:** Design proposal, structure finalised, per-framework mappings blocked on qualified legal review
**Extension URI:** https://github.com/ravikiran438/agent-consent-protocol/extensions/regulatory-context/v1
**First published:** 2026-04-16
**Depends on:** ACAP Core v0.1+, Category Preferences Extension (for the obligation-encoding grid)
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

This extension defines the machine-readable envelope by which
jurisdictional regulatory obligations (HIPAA, GDPR, PCI-DSS, CCPA,
EU AI Act, COPPA, sector-specific frameworks) travel through the ACAP
consent chain as floors that neither the callee's policy claims nor
the principal's preferences can lower. It is the mechanism by which
each industry's existing consent playbook plugs into ACAP without
ACAP itself encoding the legal content of those playbooks.

## Primitives this extension adds

- `RegulatoryContext`, a field on both `PolicyDocument` (callee's
  declared compliance context) and `ConsentRecord` (caller's declared
  compliance context)
- `ComplianceObligation`, a structured constraint consisting of
  (framework, article, category, dimension, minimum sensitivity level)
- `Role`, an enum declaring the declaring party's position under the
  framework (data controller, data processor, covered entity, business
  associate, merchant, deployer, provider)
- `obligation_floor` computation: the per-(category, dimension) cell
  takes the strictest minimum across principal preference, callee
  declaration, and caller declaration

The intended industry-specific playbooks this envelope is designed to
carry include HIPAA authorisations, GDPR Art. 6/9 lawful bases,
PCI-DSS cardholder-data rules, CCPA categories, EU AI Act Article 50
deployer obligations, 42 CFR Part 2, COPPA verifiable parental
consent, and MiFID II client categorisation. ACAP provides the
structure; the legal content of each framework mapping is supplied by
qualified domain specialists, not by the protocol.

## Interop points with ACAP Core

- `PolicyDocument.regulatory_contexts` (new optional repeated field)
  carries the callee's declared frameworks
- `ConsentRecord.regulatory_contexts` (new optional repeated field)
  carries the caller's declared frameworks
- At evaluation time, an `AdherenceEvent` MUST honour the strictest
  floor across all declared contexts before permitting an action
- The `category-preferences` extension's (category, dimension) grid
  is the encoding surface for obligation cells

## What exists today

- High-level framing in `README.md`
- Sketch of the `effective_sensitivity = max(principal, callee, caller)`
  rule
- Role enum draft covering GDPR, HIPAA, PCI-DSS, EU AI Act role
  vocabularies

## What is open

- Protobuf schema for `RegulatoryContext` and `ComplianceObligation`
- Legal review of candidate HIPAA / GDPR / PCI-DSS / EU AI Act
  mappings before any of them are published as reference material
- A working group to maintain obligation libraries as regulations
  change
- Reference implementation that ingests a `RegulatoryContext` and
  applies the floor at `AdherenceEvent` evaluation time

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
