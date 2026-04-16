# Regulatory Context: Status

**Stage:** Design proposal, blocked on legal review
**Specification:** Not yet drafted
**Implementation:** Not yet started
**Depends on:** Anumati Core v0.1+, Category Preferences Extension

## What exists

- High-level framing in `README.md`
- Sketch of the `effective_sensitivity = max(principal, callee, caller)`
  rule

## What's open

- Legal review of any proposed HIPAA / GDPR / PCI-DSS / EU AI Act
  translations before they are standardised
- Protobuf schema for `RegulatoryContext` and `ComplianceObligation`
- A working group to maintain the obligation libraries over time
  (regulations change; the library must track them)

## What will NOT ship without qualified review

- Normative mappings of specific regulatory articles to
  (category, dimension) tuples
- Claims that a particular ACAP deployment satisfies a particular
  regulation

The protocol can provide the *structure* to carry such mappings
without making the mappings themselves part of the spec. That's the
boundary we'd propose to draw.

## Seeking

If you are a compliance engineer, data-protection lawyer, or
healthcare-law specialist and would be interested in collaborating on
this extension, please open an issue on the parent repository.
