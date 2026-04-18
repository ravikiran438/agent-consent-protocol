# Audit Projection Extension

An extension to Anumati Core that derives **plain-English audit
reports** from the consent chain and adherence trail.

## The problem

The consent chain and adherence trail are built for machines. They
are structured so that agents can create, verify, and query them
efficiently.

But the actual audience for this data is human: compliance officers,
legal teams, regulators, and the principals themselves. A
machine-readable audit trail that requires an engineer to interpret
loses a large part of its value.

A regulator asking "did this agent honour §3.4.2?" should not get a
JSON dump.

## The design direction

Define a `GenerateAuditReport` RPC that walks the consent chain and
adherence trail for a given caller-callee pair over a time range and
produces a structured, plain-English report with three parts:

1. **Executive summary**, 2–3 paragraph narrative covering the audit
   window (policy versions used, consent decisions made, invocations
   permitted vs. denied)
2. **Chronological timeline**, each `ConsentRecord` and
   `AdherenceEvent` rendered as a timestamped narrative entry, with
   the agent's own reasoning quoted verbatim from the `reasoning`
   field
3. **Per-claim and per-version summaries**, statistical breakdowns
   showing, for each claim, how many evaluations, permits, denies,
   and escalations; and for each policy version, when it was active
   and how many events occurred under it

The report is a **projection**, it contains no data not already in
the chain. An auditor who doubts the narrative can follow the
cross-references to the signed records.

## Why it's separated from Core

Report generation is a presentation layer. Core defines the canonical
machine-readable records; this extension defines one way to render
them for human consumption.

Other rendering formats are possible: visual timelines, IDE
inspector panels, Excel exports. Keeping this out of Core lets
alternative renderings emerge without bloating the protocol.

## Relevance to regulation

The chronological timeline and per-claim summaries provide the kind of
"meaningful information about the logic involved" that
[GDPR Recital 71](https://gdpr-info.eu/recitals/no-71/) and
[Art. 13(2)(f)](https://gdpr-info.eu/art-13-gdpr/) /
[14(2)(g)](https://gdpr-info.eu/art-14-gdpr/) contemplate for
automated decision-making under
[Art. 22](https://gdpr-info.eu/art-22-gdpr/). This extension exists
in large part to make that compliance story concrete.
