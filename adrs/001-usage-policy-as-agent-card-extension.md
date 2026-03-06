# ADR 001: Usage Policy as an A2A Agent Card Extension

**Status:** Accepted
**Date:** 2026-03-03
**Authors:** ACAP Working Group

---

## Context

The A2A Agent Card communicates what an agent *can* do (capabilities, skills,
security schemes). It has no mechanism for communicating what calling agents
*are permitted to do* under the callee's Terms of Service or Privacy Policy.

Three alternative attachment points were considered:

1. **A2A message payload header** – policy reference included in every
   Task or Message sent to the callee.
2. **Separate discovery endpoint** – a new well-known URL published
   independently of the AgentCard.
3. **Agent Card extension** – policy reference added to the AgentCard via
   the existing `capabilities.extensions` mechanism.

## Decision

We attach the usage policy reference to the A2A Agent Card via
`capabilities.extensions`, adding a top-level `usage_policy` field of type
`UsagePolicyRef`.

## Rationale

**Against option 1 (message header):** Policy is a property of the callee
agent, not of individual tasks. Repeating a policy reference in every
message is redundant and creates a synchronisation problem when the policy
version changes mid-session.

**Against option 2 (separate endpoint):** A separate discovery mechanism
would require calling agents to perform an additional discovery step before
every new callee interaction. The Agent Card is already the discovery
primitive in A2A; splitting discovery across two mechanisms adds complexity
without benefit.

**For option 3 (Agent Card extension):**

- `capabilities.extensions` is the established A2A extensibility pattern,
  used by AP2 for payment protocol declaration.
- A single AgentCard fetch gives the caller everything needed: capability
  advertisement, authentication requirements, AND policy reference.
- Setting `required: true` on the extension allows callees to signal that
  ACAP compliance is mandatory, using the same mechanism A2A already defines
  for required extensions.
- The `document_hash` in `UsagePolicyRef` provides tamper-evidence for the
  policy pointer itself, not just the document it references.

## Consequences

- Calling agents MUST refresh their cached AgentCard before each session
  (or on a short TTL) to detect policy version bumps.
- Callee agents that add ACAP support increment only their AgentCard; no
  other protocol messages change.
- The `/.well-known/usage-policy.json` well-known URL is a convention, not
  enforced by the AgentCard. The authoritative URL is `document_uri` in the
  `UsagePolicyRef`.
