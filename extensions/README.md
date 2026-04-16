# Anumati Extensions

This directory hosts protocol extensions that build on Anumati Core (the
three-primitive consent chain specified at the repository root). Each
extension is maintained independently with its own specification,
status, and feedback thread.

Extensions are not separate preprints. They live here, evolve here, and
graduate to full specifications as each one matures through community
review and implementation.

## Status conventions

Each extension declares its stage in `STATUS.md`:

- **Design proposal**, problem framed, high-level design sketched
- **Specification in progress**, TLA+ and/or proto being drafted
- **Reference implementation**, code exists, tests pass
- **Adopted**, in production use by at least one agent framework

## Current extensions

| Extension | Stage | What it adds |
|---|---|---|
| [governance-tiering](./governance-tiering/) | Design proposal | Tiered escalation with a governance agent; three-hop delegation chains |
| [category-preferences](./category-preferences/) | Design proposal | Asymmetric sensitivity preferences across data category × usage dimension |
| [regulatory-context](./regulatory-context/) | Design proposal | Jurisdictional floors (GDPR/HIPAA/PCI-DSS) as structured obligations |
| [audit-projection](./audit-projection/) | Design proposal | Plain-English audit reports derived from consent chain + adherence trail |

## Contributing

Extensions are open to contribution. For each extension, see its own
`README.md` for the problem it addresses and the design direction, and
`STATUS.md` for what's done and what's open. Pull requests welcome.
