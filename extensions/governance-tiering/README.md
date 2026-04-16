# Governance Tiering Extension

An extension to Anumati Core that adds a **governance agent**.
a supervisory component that evaluates the materiality of policy changes
before deciding whether to escalate to the human principal.

## The problem

Anumati Core requires a new `ConsentRecord` on every `PolicyDocument`
version bump. For agents operating in high-throughput environments,
this produces alert fatigue: every minor wording change in a policy
would interrupt the human principal.

Not every re-consent event deserves human attention. A callee fixing
a typo, tightening a constraint, or adding a claim that already aligns
with the caller's existing mandate should not trigger a modal dialog.

## The design direction

Introduce a `governance_agent` as an optional third party that reviews
policy diffs and classifies them into escalation tiers:

- `auto_approved`, immaterial change, no human involvement
- `governance_reviewed`, material but within delegated authority
- `human_required`, material + high stakes, blocks until the human acts

The governance agent's assessment is recorded as an
`EscalationAssessment` on the `ConsentRecord`, making the delegation
decision auditable.

## Related features

- **Tiered escalation**, the `auto_approved` / `governance_reviewed` /
  `human_required` classification
- **Materiality criteria**, structural checks (new claims, removed
  permissions, `rule_type` changes) plus optional LLM-assisted semantic
  interpretation for "relaxed" vs "tightened" constraints
- **Delegation boundary**, the governance agent operates under a
  meta-policy from the principal defining what may be auto-approved
- **Three-hop delegation**, extends the consent chain with a
  `delegation_chain` field for Agent A → Agent B → Agent C paths

## Why it's separated from Core

Governance tiering is a policy-engineering concern, not a protocol
concern. Anumati Core defines the consent chain; this extension
defines one pattern for who reviews what when the chain grows.

Other review patterns are possible (e.g., per-domain policy review,
reputation-weighted review). Keeping this out of Core lets alternative
patterns emerge without forking the spec.
