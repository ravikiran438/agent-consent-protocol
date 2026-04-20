# ACAP MCP Server — Sample Payloads

Ready-to-paste JSON for every tool exposed by `acap-mcp`. Drop any
block at an MCP-compatible client (VSCode, MCP Inspector, or any
stdio-capable MCP host) with an invocation like:

> Call `validate_consent_chain` with this input: `<paste>`

Each tool has one happy-path payload (returns `"ok": true`) and a
note on how to trip the failure path. Hashes are placeholder
`sha256:0…0`; for true hash validation, run `compute_policy_hash`
first and substitute the result.

---

## compute_policy_hash

**What it does:** canonical SHA-256 over a PolicyDocument.

```json
{
  "policy": {
    "version": "1.0.0",
    "document_uri": "https://callee.example.com/policy/1.0.0.json",
    "document_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "effective_date": "2026-03-01T00:00:00Z",
    "claims": [
      {
        "claim_id": "a",
        "clause_ref": "§a",
        "action": "odrl:aggregate",
        "asset": "pii:session_data",
        "rule_type": "prohibition",
        "effective_version": "1.0.0"
      }
    ],
    "publisher": "https://callee.example.com/agent",
    "natural_language_uri": "https://callee.example.com/terms"
  }
}
```

**Failure variant:** pass a PolicyDocument missing `publisher` (required
field) to see the Pydantic error surface as an MCP error.

---

## validate_consent_chain

**What it does:** verifies prev_record_id linkage, caller/callee
consistency, and (when policies are supplied) claim coverage and
hash match.

```json
{
  "chain": [
    {
      "record_id": "rec-1",
      "prev_record_id": null,
      "caller_agent_id": "did:agent:caller",
      "callee_agent_id": "https://callee.example.com/agent",
      "policy_version": "1.0.0",
      "policy_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
      "parsed_claims": [
        {"claim_id": "a", "understood": true, "disputed": false}
      ],
      "decision": "accepted",
      "accepted_at": "2026-03-01T10:00:00Z",
      "valid_until": "on_version_bump"
    }
  ]
}
```

**Failure variant:** add a second record with
`"prev_record_id": "rec-not-real"` to break link integrity.

---

## validate_adherence_trail

**What it does:** verifies prev_event_id linkage and that every event
anchors to a consent record in the supplied chain.

```json
{
  "chain": [
    {
      "record_id": "rec-1",
      "prev_record_id": null,
      "caller_agent_id": "did:agent:caller",
      "callee_agent_id": "https://callee.example.com/agent",
      "policy_version": "1.0.0",
      "policy_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
      "parsed_claims": [{"claim_id": "a", "understood": true, "disputed": false}],
      "decision": "accepted",
      "accepted_at": "2026-03-01T10:00:00Z",
      "valid_until": "on_version_bump"
    }
  ],
  "trail": [
    {
      "event_id": "ev-1",
      "prev_event_id": null,
      "consent_record_id": "rec-1",
      "action": "odrl:aggregate",
      "clause_evaluated": "§a",
      "claim_id": "a",
      "decision": "permit",
      "reasoning": "action matches a permitted claim",
      "timestamp": "2026-03-01T10:05:00Z"
    }
  ]
}
```

**Failure variant:** change `consent_record_id` on the event to
`"rec-unknown"` to trip the anchor check.

---

## classify_policy_bump (governance-tiering extension)

**What it does:** diffs two PolicyDocument versions and returns the
tier (`auto_approved` / `governance_reviewed` / `human_required`)
plus the structural signals that fired.

```json
{
  "previous_policy": {
    "version": "1.0.0",
    "document_uri": "https://callee.example.com/policy/1.0.0.json",
    "document_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "effective_date": "2026-03-01T00:00:00Z",
    "claims": [
      {"claim_id": "a", "clause_ref": "§a", "action": "odrl:aggregate", "asset": "pii:session_data", "rule_type": "prohibition", "effective_version": "1.0.0"},
      {"claim_id": "b", "clause_ref": "§b", "action": "odrl:aggregate", "asset": "pii:session_data", "rule_type": "prohibition", "effective_version": "1.0.0"}
    ],
    "publisher": "https://callee.example.com/agent",
    "natural_language_uri": "https://callee.example.com/terms"
  },
  "current_policy": {
    "version": "2.0.0",
    "document_uri": "https://callee.example.com/policy/2.0.0.json",
    "document_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "effective_date": "2026-03-05T00:00:00Z",
    "claims": [
      {"claim_id": "a", "clause_ref": "§a", "action": "odrl:aggregate", "asset": "pii:session_data", "rule_type": "prohibition", "effective_version": "1.0.0"}
    ],
    "publisher": "https://callee.example.com/agent",
    "natural_language_uri": "https://callee.example.com/terms"
  },
  "governance_agent_id": "did:agent:governance"
}
```

**What trips each tier:**
- **auto_approved:** metadata-only bumps (`diff_policies` actually
  rejects these, so this tier is rare for structural diffs).
- **governance_reviewed:** add a new claim (removed the removal above;
  add `claim-b` in current_policy with no `escalate_on_deny`).
- **human_required** (the example above): remove a claim, invert
  `rule_type`, remove a constraint, or add `escalate_on_deny: true`.

---

## resolve_sensitivity (category-preferences extension)

**What it does:** resolves one cell of the principal's
(category × dimension) sensitivity matrix.

```json
{
  "preferences": [
    {"category": "biometric", "sensitivity": "high"},
    {"category": "biometric", "sensitivity": "low", "dimension": "access"}
  ],
  "category": "biometric",
  "dimension": "access"
}
```

Returns `{"sensitivity": "low"}` — the specific cell wins over the
default row.

**Failure variant (not really a failure):** pass
`"category": "nonexistent"` to surface an MCP error.

---

## compute_floor (regulatory-context extension)

**What it does:** returns the strictest sensitivity across
principal preferences and all declared regulatory contexts.

```json
{
  "principal_preferences": [
    {"category": "health", "sensitivity": "low"}
  ],
  "contexts": [
    {
      "framework": "hipaa",
      "role": "covered_entity",
      "obligations": [
        {
          "obligation_ref": "HYPOTHETICAL-1",
          "affected_categories": ["health"],
          "affected_dimensions": ["third_party_sharing"],
          "minimum_sensitivity": "high",
          "description": "test obligation (hypothetical)"
        }
      ]
    }
  ],
  "category": "health",
  "dimension": "third_party_sharing"
}
```

Returns `{"sensitivity": "high"}` — principal is LOW but the
regulatory floor overrides.

---

## generate_audit_report (audit-projection extension)

**What it does:** projects a consent chain + adherence trail into a
regulator-facing report with timeline, per-claim summaries, and
per-version summaries.

```json
{
  "request": {
    "caller_agent_id": "did:agent:caller",
    "callee_agent_id": "https://callee.example.com/agent"
  },
  "consent_chain": [
    {
      "record_id": "rec-1",
      "prev_record_id": null,
      "caller_agent_id": "did:agent:caller",
      "callee_agent_id": "https://callee.example.com/agent",
      "policy_version": "1.0.0",
      "policy_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
      "parsed_claims": [{"claim_id": "a", "understood": true, "disputed": false}],
      "decision": "accepted",
      "accepted_at": "2026-03-01T10:00:00Z",
      "valid_until": "on_version_bump"
    }
  ],
  "adherence_trail": [
    {
      "event_id": "ev-1",
      "prev_event_id": null,
      "consent_record_id": "rec-1",
      "action": "odrl:aggregate",
      "clause_evaluated": "§a",
      "claim_id": "a",
      "decision": "permit",
      "reasoning": "test reasoning",
      "timestamp": "2026-03-01T10:05:00Z"
    }
  ]
}
```

**Optional filters:** add `from_timestamp`, `to_timestamp`,
`policy_versions`, `claim_ids`, `decision_filter` (e.g.
`["deny", "escalate"]`) to the `request` object to scope the report.

---

## validate_audit_report (audit-projection extension)

**What it does:** round-trip check on a report previously returned by
`generate_audit_report` — verifies timeline chronology, sequence
indexing, back-references, and per-claim count consistency.

Pass the `report` object from `generate_audit_report`'s response
under the `"report"` key:

```json
{
  "report": { ...report returned by generate_audit_report... }
}
```

**Failure variant:** mutate `report.timeline[0].sequence` to `999`
to trip the sequencing invariant.
