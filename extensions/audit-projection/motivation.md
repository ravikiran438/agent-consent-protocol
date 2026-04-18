# Audit Projection: Why This Extension Exists

This document explains the motivation for the audit-projection
extension to the Agent Consent and Adherence Protocol (ACAP). Section 1
describes the audience mismatch between ACAP's machine-readable records
and the humans who actually need to read them. Section 2 describes why
Core alone cannot bridge the gap. Section 3 describes our approach: a
deterministic, lossless projection from signed records into a
regulator-facing report. Section 4 compares the design against
alternatives we considered. Section 5 fences off what this extension
does not attempt.

## 1. The problem

ACAP Core produces two append-only structures for every caller-callee
pair: the consent chain and the adherence trail. Both are designed for
machines. The linked-list structure makes integrity checking fast, the
fields are normalized for deterministic hashing, and every record is
signed. An auditing agent can verify in milliseconds that a chain has
not been tampered with and that every claim was parsed before action.

So the machine side works. The human side does not.

The humans who actually consume audit data are not engineers. They are
compliance officers reviewing whether a deployment met its
[HIPAA minimum-necessary](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.502)
obligations, data-protection officers drafting an
[EU AI Act Annex IV](https://artificialintelligenceact.eu/annex/4/)
technical-documentation file, legal teams preparing for a regulator
inquiry, and principals themselves who want to know what an agent
did on their behalf. A JSON dump of a linked list does not answer the
questions any of these people are paid to ask.

A regulator who asks "did Agent X honor §3.4.2 during the period
March 1 through March 5?" is asking a question the protocol can
answer, but not in a form the regulator can use. The answer lives in
the adherence trail, filtered by time window and claim id, with the
reasoning fields concatenated into a narrative. Producing that
narrative by hand from JSON takes an engineer half a day. Producing it
from a language model is fast but introduces the very problem the
chain was designed to solve: the chain is signed and reproducible, a
language-model summary is neither.

The gap between what the chain records and what an auditor can read
is where audit cost accrues in every regulated industry, and it is
the gap this extension fills.

## 2. Why core alone is insufficient

Core's contribution is to make every claim-level decision recordable,
referenceable, and verifiable. It is silent on how that record should
be rendered. A Core-only deployment forces every audit consumer to
build a rendering layer independently, which produces three bad
outcomes.

First, two compliance officers reading the same chain with different
rendering tools will produce different narratives. The source is the
same signed records, the rendered prose diverges. So a regulator who
receives reports from two deployments cannot assume the reports mean
the same thing.

Second, ad-hoc rendering tools lose reproducibility. A report that
summarizes "of 47 events, 45 were permitted and 2 were denied" has
value only if a second tool can be shown to produce the same counts
from the same chain. Without a specification for the projection,
counts drift depending on who wrote the tool.

Third, the cost of rendering falls on consumers who are least
equipped to bear it. The engineer writing the original agent knows
the chain structure and can parse it; the compliance officer
receiving the chain does not and cannot. A deployment that ships
Core-only is effectively shipping engineer-hours of audit preparation
into every regulator inquiry.

What Core cannot do alone is define a reproducible projection from
its own records into a human-facing form. That is the gap this
extension fills.

## 3. Our approach

We define a single projection function, `generate_report`, that takes
the Core chain, the Core trail, an optional policy catalog, and a
request scope `(caller, callee, window, filters)`, and produces an
`AuditReport`. The report has three parts:

  1. An **executive summary**, deterministic prose covering the window
     (number of policy versions, number of consent records, permits /
     denies / escalations)
  2. A **chronological timeline**, one `AuditEntry` per record or
     event, each with a back-reference to the signed source
  3. **Per-claim and per-version summaries**, statistical breakdowns
     that are byte-identical across conformant implementations given
     the same input

The report is a *projection*, not a translation. Every narrative line
carries a cross-reference such that an auditor who doubts the prose
can dereference to the signed record and read it directly. No
information appears in the report that is not already in the chain.

Our approach has four practical properties that matter for deployment.

First, narrative rendering uses deterministic f-string templates, not
a language model. The proto explicitly allows prose style to vary
across implementations but requires the cross-references and counts
to match. So a compliance officer can receive two reports rendered
by different tools and verify they describe the same underlying
events by comparing cross-references and counts, not by comparing
prose.

Second, the projection is filterable. The request carries a time
window, a policy-version list, a claim-id list, and a decision
filter. A regulator asking "show me all denials for claim 3.4.2 in
March" gets a report scoped to that question, such that the returned
narrative is exactly the scope the question asked. Nothing outside
the scope appears; nothing inside the scope is omitted.

Third, the projection is composable with the other extensions. A
deployment using the governance-tiering extension attaches
`EscalationAssessment` entries to its records, and a future version
of the projector can render those as `GOVERNANCE_AUTO`,
`GOVERNANCE_REVIEWED`, and `HUMAN_REVIEW` timeline entries (the enum
is already in the proto). A deployment using the regulatory-context
extension can surface per-obligation compliance sections in the
report. The current reference implementation stays focused on Core
records; the extension points are reserved but not wired.

Fourth, the validator enforces exactly the invariants an auditor
relies on: 1-based consecutive sequence indexing, chronological
timeline, every entry carrying at least one back-reference, and
per-claim summary counts matching the timeline's adherence events.
These are the properties that make the report trustworthy; the
validator will reject a report that violates any of them.

## 4. Alternatives considered

We considered four alternatives to the projection-function approach
before settling on it.

**Language-model-generated prose.** A caller passes the chain to a
language model with a prompt asking for an audit summary. Appealing
for fluency, unworkable for reproducibility: two models will produce
two summaries, and the consumer has no deterministic way to check
that both describe the same underlying events. Rejected in favor of
deterministic templates.

**Visual-only reports.** A dashboard renders the chain as a Gantt
chart, a decision timeline, and a claim heatmap, with no prose
output. Good for humans-in-the-loop during operations, poor for the
asynchronous audit case where a regulator requests a document they
can attach to a file. We treat visual rendering as a separate
concern; this extension produces the structured artifact a
dashboard-layer consumer would render.

**In-band summaries on every record.** Each `ConsentRecord` carries a
narrative field generated at record time, such that the chain is
already human-readable. This bloats every record with prose that
most consumers never read, and it loses the ability to produce
scoped reports (the prose is per-record, not per-query). Out.

**Specialized SQL / Cypher views.** The chain is stored in a database
and audit queries become SQL. This is effectively what sophisticated
deployments will do anyway, but specifying SQL schemas in the ACAP
repository ties the protocol to a storage choice that is out of
scope. The projection function is storage-agnostic; a caller that
stores the chain in Postgres or in a graph database can both call
`generate_report` with the same inputs.

## 5. Out of scope

This extension proposes a minimal base. It does not specify how
reports are stored, signed, or transmitted; how a language layer
provides multi-language rendering (the `language` field is in the
proto but the reference implementation supports English only); how a
report is cryptographically bound to a specific chain state beyond the
back-references; or how reports compose into cross-callee aggregate
views. Each of these is a real problem and each deserves its own
specification.

The intended regulatory touchpoints this extension speaks to are the
[GDPR Recital 71](https://gdpr-info.eu/recitals/no-71/) and
[Art. 13(2)(f)](https://gdpr-info.eu/art-13-gdpr/) /
[14(2)(g)](https://gdpr-info.eu/art-14-gdpr/) expectations for
"meaningful information about the logic involved" in automated
decision-making under [Art. 22](https://gdpr-info.eu/art-22-gdpr/),
and the [EU AI Act Annex IV](https://artificialintelligenceact.eu/annex/4/)
technical-documentation requirements for high-risk deployments. The
report's structure is deliberately designed to answer the questions
those frameworks contemplate, without the extension making any claim
that the report by itself satisfies the frameworks. Satisfaction is a
legal determination supplied by the deployment, not the protocol.

## References

The regulatory touchpoints informing the report's structure:
[GDPR Recital 71](https://gdpr-info.eu/recitals/no-71/),
[GDPR Art. 13(2)(f)](https://gdpr-info.eu/art-13-gdpr/),
[GDPR Art. 14(2)(g)](https://gdpr-info.eu/art-14-gdpr/),
[GDPR Art. 22](https://gdpr-info.eu/art-22-gdpr/), and
[EU AI Act Annex IV](https://artificialintelligenceact.eu/annex/4/).
For the Core ACAP specification this extension builds on, see the
paper at [Zenodo DOI 10.5281/zenodo.19606339](https://doi.org/10.5281/zenodo.19606339).
