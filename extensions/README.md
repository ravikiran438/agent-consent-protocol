# ACAP Extensions

This directory hosts protocol extensions that build on ACAP Core (the
three-primitive consent chain specified at the repository root). Each
extension is maintained independently with its own specification,
status, and feedback thread.

Extensions are not separate preprints. They live here, evolve here, and
graduate to full specifications as each one matures through community
review and implementation.

## Status conventions

Each extension declares its stage in `STATUS.md`:

- **Design proposal**, problem framed, scope fenced, primitives named
- **Specification in progress**, TLA+ and/or proto being drafted
- **Reference implementation**, code exists, tests pass
- **Adopted**, in production use by at least one agent framework

Each `STATUS.md` also carries the extension's stable URI, first
publication date, dependencies, and the engineering boundaries that
separate it from ACAP Core and from the other extensions.

## Current extensions

| Extension | Stage | First published | Scope (one sentence) |
|---|---|---|---|
| [governance-tiering](./governance-tiering/) | Reference implementation | 2026-04-16 | Tiered escalation of ACAP policy-version bumps by materiality, with an optional `governance_agent` whose classification decisions are themselves recorded in the consent chain. |
| [category-preferences](./category-preferences/) | Reference implementation | 2026-04-16 | Principal-declared asymmetric sensitivity across a data-category x usage-dimension grid, travelling with the `ConsentRecord` per callee. |
| [regulatory-context](./regulatory-context/) | Reference implementation (envelope); per-framework mappings blocked on legal review | 2026-04-16 | Machine-readable envelope by which jurisdictional floors ([HIPAA](https://www.hhs.gov/hipaa/index.html), [GDPR](https://gdpr-info.eu/), [PCI-DSS](https://www.pcisecuritystandards.org/), [CCPA](https://oag.ca.gov/privacy/ccpa), [EU AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)) travel through the consent chain; each industry playbook plugs in without ACAP encoding its legal content. |
| [audit-projection](./audit-projection/) | Reference implementation | 2026-04-16 | Regulator-facing human-readable projection of the ACAP consent chain and adherence trail, sufficient for [GDPR Recital 71](https://gdpr-info.eu/recitals/no-71/) disclosures and [EU AI Act Annex IV](https://artificialintelligenceact.eu/annex/4/) documentation. |

## Contributing

Extensions are open to contribution. For each extension, see its own
`README.md` for the problem it addresses and the design direction, and
`STATUS.md` for what is done, what is open, and what is explicitly
out of scope. Pull requests welcome.

New extensions MAY be proposed by opening an issue on the parent
repository with a scope sketch that names the problem addressed, the
primitives introduced, and the engineering boundary against ACAP
Core and the other extensions.
