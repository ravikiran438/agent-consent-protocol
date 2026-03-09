# Agent Consent and Adherence Protocol (ACAP) Specification

**Version:** 0.1.0-draft
**Status:** Draft
**Published:** 2026-03-03
**Extension URI:** `https://github.com/ravikiran438/agent-consent-protocol/v1`
**Normative definition:** [`specification/consent.proto`](../specification/consent.proto)

---

## Table of Contents

- [Agent Consent and Adherence Protocol (ACAP) Specification](#agent-consent-and-adherence-protocol-acap-specification)
  - [Table of Contents](#table-of-contents)
  - [1. Introduction](#1-introduction)
    - [1.1 Goals](#11-goals)
    - [1.2 Guiding Principles](#12-guiding-principles)
    - [1.3 Relationship to A2A and AP2](#13-relationship-to-a2a-and-ap2)
    - [1.4 Specification Structure](#14-specification-structure)
  - [2. Terminology](#2-terminology)
  - [3. The Consent Gap in A2A](#3-the-consent-gap-in-a2a)
    - [3.1 Why Auth Policy Alone Is Insufficient](#31-why-auth-policy-alone-is-insufficient)
    - [3.2 Proof of Acceptance vs. Proof of Adherence](#32-proof-of-acceptance-vs-proof-of-adherence)
    - [3.3 UETA §14 and Agent Liability](#33-ueta-14-and-agent-liability)
  - [4. Data Model](#4-data-model)
    - [4.1 PolicyDocument](#41-policydocument)
    - [4.2 PolicyClaim](#42-policyclaim)
    - [4.3 UsagePolicyRef](#43-usagepolicyref)
    - [4.4 ConsentRecord](#44-consentrecord)
    - [4.5 ParsedClaim](#45-parsedclaim)
    - [4.6 AdherenceEvent](#46-adherenceevent)
  - [5. Protocol Operations](#5-protocol-operations)
    - [5.1 GetPolicy](#51-getpolicy)
    - [5.2 RecordConsent](#52-recordconsent)
    - [5.3 GetConsentRecord](#53-getconsentrecord)
    - [5.4 ListConsentHistory](#54-listconsenthistory)
    - [5.5 RecordAdherence](#55-recordadherence)
    - [5.6 ListAdherenceEvents](#56-listadherenceevents)
    - [5.7 CheckAdherence](#57-checkadherence)
  - [6. Agent Card Extension](#6-agent-card-extension)
    - [6.1 Extension Declaration](#61-extension-declaration)
    - [6.2 UsagePolicyRef Field](#62-usagepolicyref-field)
    - [6.3 Well-Known URL](#63-well-known-url)
  - [7. Consent Handshake Flow](#7-consent-handshake-flow)
    - [7.1 Initial Handshake](#71-initial-handshake)
    - [7.2 Version Bump Re-Acceptance](#72-version-bump-re-acceptance)
    - [7.3 Skill Invocation with Adherence Recording](#73-skill-invocation-with-adherence-recording)
  - [8. Policy Versioning](#8-policy-versioning)
    - [8.1 Semantic Versioning Rules](#81-semantic-versioning-rules)
    - [8.2 Material vs. Non-Material Changes](#82-material-vs-non-material-changes)
    - [8.3 Version Bump Invalidation](#83-version-bump-invalidation)
  - [9. Consent Record Chain](#9-consent-record-chain)
    - [9.1 Linked List Structure](#91-linked-list-structure)
    - [9.2 Chain Integrity Verification](#92-chain-integrity-verification)
    - [9.3 Storage Requirements](#93-storage-requirements)
  - [10. Cryptographic Signatures](#10-cryptographic-signatures)
  - [11. ODRL Vocabulary Alignment](#11-odrl-vocabulary-alignment)
  - [12. Security Considerations](#12-security-considerations)
  - [13. Privacy Considerations](#13-privacy-considerations)
  - [14. Normative References](#14-normative-references)
  - [15. Informative References](#15-informative-references)

---

## 1. Introduction

The Agent Consent and Adherence Protocol (ACAP) extends the
[Agent2Agent (A2A) Protocol](https://a2a-protocol.org/latest/) with a
first-class mechanism for versioned, machine-readable usage policy
attachment and append-only consent auditing between AI agents.

As AI agents increasingly call other agents autonomously, the question of
what an agent is **permitted** to do diverges from the question of what an
agent is **capable** of doing. The A2A Agent Card communicates capability.
ACAP communicates policy—and provides the audit infrastructure to prove that
policy was understood and honoured at runtime.

### 1.1 Goals

- **G1 – Policy as a first-class A2A citizen.** Attach versioned,
  machine-readable usage policies to A2A Agent Cards via the standard
  `capabilities.extensions` mechanism.

- **G2 – Proof of adherence, not just proof of acceptance.** Replace the
  human "I clicked agree" model with a clause-level reasoning record that
  agents produce at every skill invocation.

- **G3 – Legally defensible audit trail.** Maintain an append-only
  singly-linked chain of consent records and adherence events that
  establishes accountability under UETA §14, GDPR Art. 7(1), and
  equivalent frameworks.

- **G4 – Version-gated re-acceptance.** Automatically invalidate cached
  consent when a callee publishes a new PolicyDocument version, blocking
  skill invocation until the caller records fresh consent.

- **G5 – ODRL vocabulary alignment.** Express policy rules using W3C ODRL
  2.2 action/asset/rule vocabulary to maximise interoperability with
  existing rights-management infrastructure.

- **G6 – Human principal protection.** When an agent acts on behalf of a
  human principal, surface the principal's identity in consent records to
  close the UETA §14 liability gap.

### 1.2 Guiding Principles

**Normative source of truth.** The file `specification/consent.proto` is
the single authoritative normative definition of all protocol data objects.
This specification document is the narrative elaboration; in case of
conflict, the proto file governs.

**Additive, not replacement.** ACAP does not replace A2A authentication
(OAuth 2.x, API keys, mTLS). It adds a semantic policy layer above the
transport security layer.

**Agents reason; humans click.** ACAP is designed for agents that can parse
and reason about policy text. It does not attempt to replicate human consent
UX. The `reasoning` field on `AdherenceEvent` is the mechanism by which
agent reasoning is captured and made auditable.

**Immutability by convention.** Consent records and adherence events are
append-only. Neither party may delete or modify a committed record. Storage
backends SHOULD enforce this via write-once semantics.

**Minimal footprint.** ACAP adds exactly three objects to the A2A surface:
`PolicyDocument`, `ConsentRecord`, and `AdherenceEvent`. Everything
else is derived.

### 1.3 Relationship to A2A and AP2

```
┌─────────────────────────────────────────────────────────────┐
│                        ACAP Layer                           │
│   PolicyDocument · ConsentRecord · AdherenceEvent      │
│   (What agents may do and the proof that they did it right) │
├─────────────────────────────────────────────────────────────┤
│                        AP2 Layer                            │
│   IntentMandate · CartMandate · PaymentMandate              │
│   (What agents are authorised to transact)                  │
├─────────────────────────────────────────────────────────────┤
│                        A2A Layer                            │
│   Task · Message · AgentCard · SecurityScheme               │
│   (How agents communicate and authenticate)                 │
└─────────────────────────────────────────────────────────────┘
```

ACAP is a peer extension to AP2: both build on A2A via the
`capabilities.extensions` mechanism, and both can be active simultaneously.
When AP2 is also in use, the `ConsentRecord.principal_id` SHOULD match
the user identity established in the AP2 mandate chain.

### 1.4 Specification Structure

This specification uses the normative keywords **MUST**, **MUST NOT**,
**REQUIRED**, **SHALL**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**,
**MAY**, and **OPTIONAL** as defined in
[RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119).

---

## 2. Terminology

**Callee Agent.** An A2A server that exposes skills and publishes a
`PolicyDocument` governing their use.

**Calling Agent.** An A2A client that invokes callee skills and is
responsible for parsing the `PolicyDocument`, recording consent, and
generating `AdherenceEvent` records.

**PolicyDocument.** A versioned, machine-readable document that expresses
the callee's usage policy as a set of `PolicyClaim` objects using ODRL 2.2
vocabulary.

**PolicyClaim.** A single machine-readable rule (permission, prohibition, or
obligation) derived from one or more natural-language clauses in the
callee's Terms of Service or Privacy Policy.

**ConsentRecord.** An append-only document recording the calling
agent's parsed understanding of and decision about a specific
`PolicyDocument` version. Records form a singly-linked list constituting
the consent chain.

**Consent Chain.** The singly-linked sequence of `ConsentRecord`
objects for a given caller-callee pair, ordered from newest to oldest via
`prev_record_id`.

**AdherenceEvent.** An append-only document recording the calling agent's
runtime policy evaluation for a single action. Events form a singly-linked
list constituting the adherence trail.

**Adherence Trail.** The singly-linked sequence of `AdherenceEvent` objects
for a given `ConsentRecord`, ordered from newest to oldest via
`prev_event_id`.

**Proof of Acceptance.** The traditional human consent model: a timestamp
and identity record proving a party clicked "I agree". Does not prove
understanding or subsequent compliance.

**Proof of Adherence.** The ACAP model: a clause-level reasoning record for
every action attempt, proving the agent evaluated policy before acting.

**Principal.** The human entity on whose behalf a calling agent acts.
Identified by `ConsentRecord.principal_id`.

**Version Bump.** Publication of a new `PolicyDocument` with a higher
semantic version, which invalidates all current `ConsentRecord`
objects for that callee.

---

## 3. The Consent Gap in A2A

### 3.1 Why Auth Policy Alone Is Insufficient

A2A authentication (OAuth 2.x scopes, API keys, mTLS) governs **who** may
call **which** endpoint. It answers the question: "Is this agent authorised
to invoke skill X?"

Usage policy governs **how** and **under what conditions** a permitted
action may be taken. It answers questions like:

- May the calling agent store the task output for cross-session analysis?
- May the calling agent aggregate results across multiple principals?
- Is the calling agent obligated to notify its principal before invoking
  this skill?

These questions cannot be encoded in OAuth scopes. Scopes are discrete,
static, and binary. Usage policy is contextual, evolving, and semantic. The
two layers are complementary, not substitutable.

### 3.2 Proof of Acceptance vs. Proof of Adherence

| Dimension          | Proof of Acceptance (human) | Proof of Adherence (ACAP)           |
|--------------------|-----------------------------|-------------------------------------|
| Granularity        | Whole document              | Per-clause, per-action              |
| Timing             | At signup / version bump    | At every skill invocation           |
| Content            | Timestamp + identity        | Clause citation + reasoning string  |
| Understanding      | Assumed (click-through)     | Verified (parsed_claims)            |
| Subsequent compliance | Unverifiable             | Auditable via adherence trail       |
| Legal value        | Proves acceptance           | Proves acceptance **and** adherence |

ACAP generates proof of adherence by requiring calling agents to:

1. Parse every `PolicyClaim` in the `PolicyDocument` and record their
   understanding in `ConsentRecord.parsed_claims`.
2. Evaluate the relevant `PolicyClaim` before every skill invocation and
   record their reasoning in `AdherenceEvent.reasoning`.

### 3.3 UETA §14 and Agent Liability

Under the Uniform Electronic Transactions Act (UETA) §14, a contract formed
by an electronic agent binds the **human principal**, not the agent itself.
The commentary treats AI as a tool: "the employer of a tool is responsible
for the results obtained by the use of that tool."

This has two consequences for A2A systems:

1. When Agent A calls Agent B and implicitly accepts Agent B's ToS, Agent
   A's principal is legally bound—without necessarily being aware.
2. When Agent A calls Agent B and the interaction causes harm, the
   principal cannot claim ignorance of the terms if the agent processed them.

ACAP addresses consequence (1) by making policy acceptance explicit,
versioned, and recorded. It addresses consequence (2) by giving principals
a chain of consent records they can inspect to understand what their agent
agreed to on their behalf.

---

## 4. Data Model

> The canonical definition of all types is in `specification/consent.proto`.
> The JSON representations below are illustrative.

### 4.1 PolicyDocument

Published by the callee agent at a well-known HTTPS URL. Hosted at
`/.well-known/usage-policy.json` by convention.

```json
{
  "version": "2.1.0",
  "document_uri": "https://callee.example.com/.well-known/usage-policy.json",
  "document_hash": "sha256:a3f5c2...",
  "effective_date": "2026-02-27T00:00:00Z",
  "supersedes": "2.0.0",
  "change_summary": "§3.4 now prohibits cross-session PII aggregation",
  "publisher": "did:web:callee.example.com",
  "natural_language_uri": "https://callee.example.com/terms",
  "jurisdictions": ["GDPR", "CCPA"],
  "claims": [
    {
      "claim_id": "3f7a1b2c-0001-7000-8000-000000000001",
      "clause_ref": "§2.1",
      "action": "odrl:use",
      "asset": "a2a:task_output",
      "rule_type": "permission",
      "constraint": null,
      "effective_version": "1.0.0",
      "escalate_on_deny": null
    },
    {
      "claim_id": "3f7a1b2c-0001-7000-8000-000000000002",
      "clause_ref": "§3.4",
      "action": "odrl:aggregate",
      "asset": "pii:session_data",
      "rule_type": "prohibition",
      "constraint": "odrl:purpose isNot behavioral_profiling",
      "effective_version": "2.1.0",
      "escalate_on_deny": true
    },
    {
      "claim_id": "3f7a1b2c-0001-7000-8000-000000000003",
      "clause_ref": "§5.1",
      "action": "a2a:notify_principal",
      "asset": "odrl:All",
      "rule_type": "obligation",
      "constraint": "a2a:task_cost greaterThan 100",
      "effective_version": "1.5.0",
      "escalate_on_deny": null
    }
  ]
}
```

**Field requirements:**

| Field              | Required | Notes |
|--------------------|----------|-------|
| `version`          | REQUIRED | Semver |
| `document_uri`     | REQUIRED | HTTPS |
| `document_hash`    | REQUIRED | `sha256:<hex>` (computed with this field set to `""`) |
| `effective_date`   | REQUIRED | ISO 8601 UTC |
| `supersedes`       | OPTIONAL | Absent on initial version |
| `change_summary`   | OPTIONAL | |
| `claims`           | REQUIRED | At least one entry |
| `publisher`        | REQUIRED | DID or HTTPS URL |
| `natural_language_uri` | REQUIRED | HTTPS |
| `jurisdictions`    | OPTIONAL | |

### 4.2 PolicyClaim

| Field               | Required | Notes |
|---------------------|----------|-------|
| `claim_id`          | REQUIRED | UUIDv4 recommended, stable across versions |
| `clause_ref`        | REQUIRED | e.g. `§3.4.2` |
| `action`            | REQUIRED | ODRL 2.2 action vocabulary preferred |
| `asset`             | REQUIRED | ODRL leftOperand vocabulary preferred |
| `rule_type`         | REQUIRED | `permission`, `prohibition`, `obligation` |
| `constraint`        | OPTIONAL | ODRL constraint expression |
| `effective_version` | REQUIRED | semver of introducing policy version |
| `escalate_on_deny`  | OPTIONAL | |

### 4.3 UsagePolicyRef

Embedded in the A2A AgentCard as the top-level `usage_policy` field.

```json
{
  "version": "2.1.0",
  "document_uri": "https://callee.example.com/.well-known/usage-policy.json",
  "document_hash": "sha256:a3f5c2...",
  "effective_date": "2026-02-27T00:00:00Z",
  "acceptance_required": true,
  "acceptance_endpoint": "https://callee.example.com/acap/consent",
  "supersedes": "2.0.0",
  "change_summary": "§3.4 now prohibits cross-session PII aggregation",
  "natural_language_uri": "https://callee.example.com/terms"
}
```

### 4.4 ConsentRecord

```json
{
  "record_id": "019500a0-0001-7000-8000-000000000001",
  "prev_record_id": "019500a0-0000-7000-8000-000000000099",
  "caller_agent_id": "did:web:caller.example.com",
  "callee_agent_id": "did:web:callee.example.com",
  "policy_version": "2.1.0",
  "policy_hash": "sha256:a3f5c2...",
  "parsed_claims": [
    {
      "claim_id": "3f7a1b2c-0001-7000-8000-000000000001",
      "understood": true,
      "disputed": false,
      "dispute_reason": null
    },
    {
      "claim_id": "3f7a1b2c-0001-7000-8000-000000000002",
      "understood": true,
      "disputed": false,
      "dispute_reason": null
    },
    {
      "claim_id": "3f7a1b2c-0001-7000-8000-000000000003",
      "understood": true,
      "disputed": false,
      "dispute_reason": null
    }
  ],
  "decision": "accepted",
  "accepted_at": "2026-02-28T10:22:00Z",
  "valid_until": "on_version_bump",
  "caller_signature": "eyJhbGciOiJFZERTQSJ9...",
  "principal_id": "user:rkadaboina@example.com"
}
```

**Linked list invariants:**

- `prev_record_id` MUST reference a record with the same `caller_agent_id`
  and `callee_agent_id`.
- `accepted_at` of this record MUST be strictly after `accepted_at` of the
  record referenced by `prev_record_id`.
- Once committed, no field MAY be modified.

**Capability fingerprint (`caller_capability_hash`):**

The `caller_capability_hash` is a SHA-256 digest computed over the canonical
JSON of the calling agent's capability fingerprint:

```json
{
  "model": "<model_id>",
  "tools": ["<sorted_tool_ids>"],
  "config": {
    "chain_of_thought": "enabled",
    "rag_enabled": "true",
    "system_prompt_hash": "sha256:<hex>",
    "temperature": "0.7"
  }
}
```

Keys are sorted lexicographically at every nesting level. The `config` object
includes parameters that materially affect policy reasoning: system prompt
hash, temperature, chain-of-thought mode, and RAG enablement.

> **Limitation:** `caller_capability_hash` is self-reported. Callees cannot
> independently verify its accuracy. See [§12](#12-security-considerations).

**Effective sensitivity formula:**

When both caller and callee declare regulatory contexts, the governance agent
computes the effective sensitivity for each (category, dimension) pair as:

```
effective = max(principal_preference, callee_obligation, caller_obligation)
```

where the total order is `LOW < MEDIUM < HIGH`. Missing entries default to
`LOW`. This ensures the strictest constraint from any source governs.

### 4.5 ParsedClaim

Every `PolicyClaim` in the `PolicyDocument` MUST have a corresponding
`ParsedClaim` in `ConsentRecord.parsed_claims`. This requirement
ensures agents cannot silently ignore inconvenient clauses.

| Field            | Required | Notes |
|------------------|----------|-------|
| `claim_id`       | REQUIRED | References `PolicyClaim.claim_id` |
| `understood`     | REQUIRED | `false` SHOULD trigger principal escalation |
| `disputed`       | REQUIRED | |
| `dispute_reason` | CONDITIONAL | REQUIRED when `disputed` is `true` |

### 4.6 AdherenceEvent

```json
{
  "event_id": "019500a0-0002-7000-8000-000000000001",
  "prev_event_id": null,
  "consent_record_id": "019500a0-0001-7000-8000-000000000001",
  "action": "aggregate_sessions",
  "clause_evaluated": "§3.4",
  "claim_id": "3f7a1b2c-0001-7000-8000-000000000002",
  "decision": "deny",
  "reasoning": "Action 'aggregate_sessions' matches prohibition §3.4 (odrl:aggregate on pii:session_data where purpose=behavioral_profiling). Callee policy v2.1.0 prohibits this. Denying and notifying principal per escalate_on_deny=true.",
  "timestamp": "2026-02-28T10:23:41Z",
  "context": {
    "task_id": "task-abc-123",
    "input_mode": "json",
    "originating_skill": "data_analysis"
  },
  "agent_signature": "eyJhbGciOiJFZERTQSJ9..."
}
```

---

## 5. Protocol Operations

ACAP exposes a `ConsentService` over HTTPS. The default transport is
JSON-RPC 2.0 (matching A2A), with gRPC as a conformant alternative binding.

### 5.1 GetPolicy

Returns the callee's current `PolicyDocument`, or a specific version if
`version` is provided.

**Request:**
```json
{ "version": null }
```

**Response:**
```json
{ "policy": { /* PolicyDocument */ } }
```

Callers MUST verify that the returned document's `document_hash` matches
the `document_hash` in the `UsagePolicyRef` on the AgentCard before
parsing claims.

### 5.2 RecordConsent

Creates a new `ConsentRecord` for the caller-callee pair. MUST be
called after the caller has parsed the `PolicyDocument` and before any
skill invocation when `acceptance_required` is `true`.

**Request:**
```json
{ "record": { /* ConsentRecord */ } }
```

**Response:**
```json
{
  "record": { /* persisted ConsentRecord */ },
  "supersedes_prior": true
}
```

The server MUST:

1. Verify that `policy_hash` matches the current `PolicyDocument` hash.
2. Verify that every `PolicyClaim.claim_id` is represented in
   `parsed_claims`.
3. If `caller_signature` is present, verify it over the canonical JSON of
   the record.
4. Assign `record_id` if not provided by the caller (servers MAY generate
   their own UUIDv7).
5. Set `prev_record_id` to the `record_id` of the most recent existing
   record for this caller-callee pair.

### 5.3 GetConsentRecord

Retrieves a specific `ConsentRecord` by `record_id`.

### 5.4 ListConsentHistory

Returns the full consent chain for a caller-callee pair, newest-first.
Supports pagination via `page_token`.

### 5.5 RecordAdherence

Appends an `AdherenceEvent` to the event chain for a given
`ConsentRecord`. Callers SHOULD call this for every skill invocation
attempt (permit or deny).

The server MUST verify that `consent_record_id` references a record in
state `accepted` or `conditional` (not `rejected`) before accepting the
event.

### 5.6 ListAdherenceEvents

Returns adherence events for a consent record, newest-first. Supports
pagination.

### 5.7 CheckAdherence

Evaluates whether a proposed action is permitted under the current bound
policy. Does **not** record an `AdherenceEvent`. Use as a pre-flight check;
use `RecordAdherence` after the action to build the auditable trail.

---

## 6. Agent Card Extension

### 6.1 Extension Declaration

Callee agents declare ACAP support by adding the ACAP extension URI to
`capabilities.extensions` in their A2A AgentCard:

```json
{
  "capabilities": {
    "extensions": [
      {
        "uri": "https://github.com/ravikiran438/agent-consent-protocol/v1",
        "description": "Supports the Agent Consent Protocol.",
        "required": true
      }
    ]
  }
}
```

Setting `required: true` signals that calling agents MUST complete the ACAP
handshake before invoking any skill. Calling agents that do not support ACAP
MUST NOT proceed with skill invocation.

### 6.2 UsagePolicyRef Field

When the ACAP extension is declared, the callee MUST also include a top-level
`usage_policy` field in the AgentCard JSON containing a `UsagePolicyRef`
object. See [§4.3](#43-usagepolicyref) for the full schema.

### 6.3 Well-Known URL

The callee MUST host the full `PolicyDocument` at:

```
https://<callee-host>/.well-known/usage-policy.json
```

The response MUST:

- Be served over HTTPS.
- Include `Content-Type: application/json`.
- Be served with `Cache-Control: no-store` or short `max-age` to prevent
  stale policy caching by callers.
- Return the document whose SHA-256 matches `UsagePolicyRef.document_hash`.

---

## 7. Consent Handshake Flow

### 7.1 Initial Handshake

```
Calling Agent                             Callee Agent
     │                                         │
     │── GET /.well-known/usage-policy.json ──►│
     │◄─ PolicyDocument (version 2.1.0) ───────│
     │                                         │
     │  [parse all PolicyClaims]               │
     │  [build ParsedClaim list]               │
     │  [decide: accepted / rejected /         │
     │           conditional]                  │
     │                                         │
     │── POST /acap/consent ──────────────────►│
     │   ConsentRecord                    │
     │◄─ RecordConsentResponse ────────────────│
     │   { record_id: "019500a0-...",          │
     │     supersedes_prior: false }           │
     │                                         │
     │  [if decision == accepted or            │
     │   conditional → proceed to skills]      │
     │                                         │
     │── POST /a2a (skill invocation) ────────►│
     │   [also POST /acap/adherence for        │
     │    each action attempted]               │
```

### 7.2 Version Bump Re-Acceptance

When the callee publishes a new `PolicyDocument` version, all existing
`ConsentRecord` objects for that callee are invalidated (those with
`valid_until: "on_version_bump"`).

Calling agents MUST detect version bumps by comparing the
`UsagePolicyRef.version` in the AgentCard (fetched fresh from
`/.well-known/agent.json`) against the `policy_version` in their current
`ConsentRecord`. If they differ:

1. Fetch the new `PolicyDocument` from `document_uri`.
2. Compute the diff against the previous version using `supersedes` and
   `change_summary`.
3. Surface material changes to the principal if `principal_id` is set.
4. Re-parse all `PolicyClaim` objects.
5. Post a new `ConsentRecord` with `prev_record_id` pointing to the
   just-invalidated record.

The new record is appended to the consent chain. The prior record is not
deleted—it remains permanently in the chain as evidence of what the agent
previously agreed to.

### 7.3 Skill Invocation with Adherence Recording

```
For each skill invocation:

1. Call CheckAdherence (pre-flight) for the action + asset.
2. If decision == PERMIT:
   a. Invoke the skill via A2A.
   b. Call RecordAdherence with decision=permit and reasoning.
3. If decision == DENY:
   a. Do NOT invoke the skill.
   b. Call RecordAdherence with decision=deny and reasoning.
   c. If PolicyClaim.escalate_on_deny == true, notify principal.
4. If decision == ESCALATE:
   a. Halt. Notify principal. Await instruction.
   b. Call RecordAdherence with decision=escalate.
```

---

## 8. Policy Versioning

### 8.1 Semantic Versioning Rules

`PolicyDocument.version` MUST follow [Semantic Versioning 2.0.0](https://semver.org/).

| Change type               | Version component | Example          |
|---------------------------|-------------------|------------------|
| New prohibition added     | MAJOR bump        | 2.0.0 → 3.0.0   |
| Existing permission narrowed | MAJOR bump     | 2.0.0 → 3.0.0   |
| New permission added      | MINOR bump        | 2.0.0 → 2.1.0   |
| Clarification, no intent change | PATCH bump  | 2.0.0 → 2.0.1   |

### 8.2 Material vs. Non-Material Changes

A **material change** is one that:

- Adds a new prohibition or obligation.
- Removes an existing permission.
- Narrows a constraint on an existing permission.
- Changes the jurisdiction list in a way that affects agent operation.

Material changes MUST result in at minimum a MINOR version bump and SHOULD
result in a MAJOR version bump. The `change_summary` field MUST describe
material changes.

A **non-material change** is one that:

- Corrects typographical errors in `clause_ref` or `change_summary`.
- Adds a `natural_language_uri` for a jurisdiction already in effect.
- Adds a new permission that does not narrow existing ones.

### 8.3 Version Bump Invalidation

All `ConsentRecord` objects with `valid_until: "on_version_bump"` for
a given callee are logically invalidated the moment the callee's
`UsagePolicyRef.version` changes. They are not deleted. The calling agent
MUST NOT invoke skills under an invalidated consent record.

---

## 9. Consent Record Chain

### 9.1 Linked List Structure

The consent chain for a given caller-callee pair is a singly-linked list:

```
[Record N]──prev──►[Record N-1]──prev──►[Record N-2]──prev──►[null]
policy: 2.1.0      policy: 2.0.0        policy: 1.5.0
```

- The head of the chain (most recent) is the **active record**.
- Every prior record is permanently accessible by traversing `prev_record_id`.
- The chain establishes the full history of what the calling agent agreed to
  on behalf of its principal, and when.

### 9.2 Chain Integrity Verification

A verifier MAY validate chain integrity by:

1. Fetching all records for a caller-callee pair via `ListConsentHistory`.
2. Verifying that `record[i].prev_record_id == record[i+1].record_id` for
   all i.
3. Verifying that `record[i].accepted_at > record[i+1].accepted_at` for
   all i.
4. If `caller_signature` is present on a record, verifying the JWS over
   the canonical JSON of that record.
5. Verifying that each record's `policy_hash` matches the hash of the
   `PolicyDocument` at the recorded `policy_version`.

### 9.3 Storage Requirements

Callee agents MUST store all `ConsentRecord` and `AdherenceEvent`
objects they receive. They MUST NOT delete or mutate committed records.

Calling agents SHOULD maintain their own local copy of all records they
have submitted. In case of dispute, the calling agent's local copy and the
callee's stored copy MUST be identical (verifiable via `caller_signature`).

Audit endpoints (third-party storage services) MAY be used by either party
to provide a neutral record. When an `acceptance_endpoint` is configured,
records submitted to it SHOULD also be retained by both parties locally.

---

## 10. Cryptographic Signatures

`ConsentRecord.caller_signature` and `AdherenceEvent.agent_signature`
MUST be JWS compact serialisations (RFC 7515) produced over the canonical
JSON of the respective object.

**Canonical JSON** is defined as:

1. The object serialised as JSON with no insignificant whitespace.
2. Object keys sorted lexicographically at every nesting level.
3. The `caller_signature` / `agent_signature` field itself MUST be excluded
   from the signed payload (set to `null` before signing).

**Algorithm:** Implementations MUST support `EdDSA` (Ed25519, RFC 8037).
Implementations SHOULD support `ES256` (P-256) for wider ecosystem
compatibility. `RS256` is NOT RECOMMENDED.

**Key resolution:** The signing key MUST be resolvable from the signer's
DID document or from a JWKS endpoint at
`<agent-host>/.well-known/jwks.json`.

---

## 11. ODRL Vocabulary Alignment

`PolicyClaim.action` and `PolicyClaim.asset` SHOULD use terms from the
W3C ODRL 2.2 vocabulary (https://www.w3.org/TR/odrl-vocab/) where
applicable. ACAP defines an extension vocabulary for A2A-specific terms:

**ACAP Action Extensions:**

| Term                     | Description |
|--------------------------|-------------|
| `a2a:invoke_skill`       | Invoke any skill on the callee agent |
| `a2a:store_output`       | Persist task output beyond the session |
| `a2a:share_output`       | Share task output with a third agent |
| `a2a:notify_principal`   | Notify the human principal |
| `a2a:cache_context`      | Cache task context across sessions |

**ACAP Asset Extensions:**

| Term                     | Description |
|--------------------------|-------------|
| `a2a:task_output`        | The output of an A2A task |
| `a2a:task_context`       | The full context of an A2A task |
| `pii:session_data`       | PII associated with a single session |
| `pii:cross_session_data` | PII aggregated across sessions |

---

## 12. Security Considerations

**Policy hash verification.** Calling agents MUST verify `document_hash`
before trusting any `PolicyDocument` fetched from `document_uri`. Failure
to verify enables a network-path attacker to substitute a more permissive
policy.

**Consent record forgery.** Callee servers MUST verify `caller_signature`
on all submitted `ConsentRecord` objects where a signature is present.
Absence of a signature does not invalidate the record but reduces its
non-repudiation value.

**Replay attacks on adherence events.** `AdherenceEvent.event_id` MUST be
unique. Callee servers SHOULD reject events whose `event_id` has been seen
before within the same `consent_record_id`.

**Version pinning.** Calling agents MUST NOT use a cached `PolicyDocument`
without comparing its hash to the current `UsagePolicyRef.document_hash`
on a fresh AgentCard fetch. Stale policy caching is a primary attack
surface.

**Principal impersonation.** `ConsentRecord.principal_id` is
informational. Callee servers MUST NOT grant elevated permissions based on
the claimed `principal_id` alone without independent verification via the
A2A authentication layer.

---

## 13. Privacy Considerations

**Record retention.** Consent records and adherence events contain agent
identifiers and timing information. Storage systems MUST enforce access
controls limiting retrieval to the caller agent, the callee agent, and
authorised audit services.

**Principal identifiers.** `principal_id` SHOULD use pseudonymous
identifiers (opaque user IDs) rather than email addresses or real names
wherever possible.

**Right to erasure.** Under GDPR Art. 17, principals may request erasure of
their personal data. Because consent records are append-only, implementors
MUST provide a pseudonymisation mechanism: on erasure request, replace
`principal_id` in all records for that principal with an irreversible hash,
and delete any supplementary fields containing personal data. The structural
integrity of the consent chain (record linkage, timestamps, hashes) MUST
be preserved.

---

## 14. Normative References

- **[A2A]** Agent2Agent Protocol Specification.
  https://a2a-protocol.org/latest/specification/
- **[ODRL]** Open Digital Rights Language (ODRL) Information Model 2.2,
  W3C Recommendation.
  https://www.w3.org/TR/odrl-model/
- **[ODRL-VOCAB]** ODRL Vocabulary & Expression 2.2, W3C Recommendation.
  https://www.w3.org/TR/odrl-vocab/
- **[RFC 2119]** Key words for use in RFCs to Indicate Requirement Levels.
  https://datatracker.ietf.org/doc/html/rfc2119
- **[RFC 7515]** JSON Web Signature (JWS).
  https://datatracker.ietf.org/doc/html/rfc7515
- **[RFC 8037]** CFRG Elliptic Curves for JOSE.
  https://datatracker.ietf.org/doc/html/rfc8037
- **[SEMVER]** Semantic Versioning 2.0.0.
  https://semver.org/
- **[PROTO3]** Protocol Buffers Language Guide (proto3).
  https://protobuf.dev/programming-guides/proto3/

---

## 15. Informative References

- **[UETA]** Uniform Electronic Transactions Act (1999).
  https://www.uniformlaws.org/committees/community-home?CommunityKey=2c04b76c-2b7d-4399-977e-d5876ba7e034
- **[GDPR-ART7]** General Data Protection Regulation, Article 7:
  Conditions for consent.
  https://gdpr-info.eu/art-7-gdpr/
- **[AIGA]** AI Governance and Accountability Protocol (IETF I-D).
  https://datatracker.ietf.org/doc/draft-aylward-aiga-1/
- **[A2A-SECURITY]** Security Requirements for AI Agents (IETF I-D).
  https://datatracker.ietf.org/doc/draft-ni-a2a-ai-agent-security-requirements/
- **[AP2]** Agent Payments Protocol.
  https://github.com/google-agentic-commerce/ap2
- **[AGENT-INDEX]** The 2025 AI Agent Index.
  https://arxiv.org/abs/2602.17753
- **[OPENMANDATE]** OpenMandate: Governing AI Agents by Authority.
  https://lawwhatsnext.substack.com/p/openmandate-governing-ai-agents-by
