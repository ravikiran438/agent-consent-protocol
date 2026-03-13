# Agent Consent and Adherence Protocol (ACAP)

**Status:** Draft v0.1.0
**Paper:** [Anumati: Proof of Adherence as a Formal Consent Model for Autonomous Agent Protocols](https://doi.org/10.5281/zenodo.18950892)
**Extension URI:** `https://github.com/ravikiran438/agent-consent-protocol/v1`
**License:** Apache 2.0

ACAP extends the [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/latest/)
with a first-class mechanism for versioned, machine-readable usage policy
attachment and append-only consent auditing between AI agents.

> **Companion protocol:** [Phala](https://arxiv.org/abs/forthcoming) (in preparation) addresses
> the outcome feedback side of the same lifecycle. ACAP governs entry — the
> conditions under which an agent may act. Phala measures exit — whether the
> action served the principal. Together they bracket agent accountability.

## The Problem

The A2A Agent Card communicates what an agent *can* do. It has no mechanism
for communicating what calling agents *are permitted to do* under the
callee's Terms of Service or Privacy Policy.

Auth policy (OAuth scopes, RBAC) governs **who** may call **which** endpoint.
Usage policy governs **how** and **under what conditions** a permitted action
may be taken. These are different layers and require different treatment.

Under UETA §14, the human principal is legally bound by whatever terms their
agent accepts—without necessarily being aware. ACAP closes this gap.

## The Solution

ACAP introduces three primitives:

| Primitive             | What it records |
|-----------------------|-----------------|
| `PolicyDocument`      | The callee's versioned, machine-readable Terms of Service |
| `ConsentRecord`  | The calling agent's parsed understanding and acceptance decision |
| `AdherenceEvent`      | The calling agent's per-action policy evaluation with reasoning |

Together they shift the consent model from **proof of acceptance**
("I clicked agree") to **proof of adherence** ("I evaluated §3.4.2 before
acting and here is my reasoning").

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ACAP Layer                           │
│   PolicyDocument · ConsentRecord · AdherenceEvent      │
├─────────────────────────────────────────────────────────────┤
│                        AP2 Layer  (optional peer)           │
│   IntentMandate · CartMandate · PaymentMandate              │
├─────────────────────────────────────────────────────────────┤
│                        A2A Layer                            │
│   Task · Message · AgentCard · SecurityScheme               │
└─────────────────────────────────────────────────────────────┘
```

## Quickstart

### 1. Declare ACAP in your Agent Card

```json
{
  "name": "MyAgent",
  "capabilities": {
    "extensions": [
      {
        "uri": "https://github.com/ravikiran438/agent-consent-protocol/v1",
        "description": "Supports the Agent Consent Protocol.",
        "required": true
      }
    ]
  },
  "usage_policy": {
    "version": "1.0.0",
    "document_uri": "https://myagent.example.com/.well-known/usage-policy.json",
    "document_hash": "sha256:e3b0c44298fc...",
    "effective_date": "2026-03-01T00:00:00Z",
    "acceptance_required": true,
    "acceptance_endpoint": "https://myagent.example.com/acap/consent",
    "natural_language_uri": "https://myagent.example.com/terms"
  }
}
```

### 2. Publish a PolicyDocument at `/.well-known/usage-policy.json`

```json
{
  "version": "1.0.0",
  "document_uri": "https://myagent.example.com/.well-known/usage-policy.json",
  "document_hash": "sha256:e3b0c44298fc...",
  "effective_date": "2026-03-01T00:00:00Z",
  "publisher": "did:web:myagent.example.com",
  "natural_language_uri": "https://myagent.example.com/terms",
  "claims": [
    {
      "claim_id": "00000000-0000-0000-0000-000000000001",
      "clause_ref": "§2.1",
      "action": "odrl:use",
      "asset": "a2a:task_output",
      "rule_type": "permission",
      "effective_version": "1.0.0"
    }
  ]
}
```

### 3. Calling agent records consent before invoking skills

```python
from acap.types import ConsentRecord, ParsedClaim, ConsentDecision

record = ConsentRecord(
    record_id="019500a0-0001-7000-8000-000000000001",
    caller_agent_id="did:web:caller.example.com",
    callee_agent_id="did:web:myagent.example.com",
    policy_version="1.0.0",
    policy_hash="sha256:e3b0c44298fc...",
    parsed_claims=[
        ParsedClaim(
            claim_id="00000000-0000-0000-0000-000000000001",
            understood=True,
            disputed=False,
        )
    ],
    decision=ConsentDecision.ACCEPTED,
    accepted_at="2026-03-04T09:00:00Z",
    valid_until="on_version_bump",
)
# POST record to acceptance_endpoint
```

## Repository Layout

```
ACAP/
├── specification/
│   └── consent.proto          # Normative proto3 definition (source of truth)
├── docs/
│   ├── specification.md       # Full protocol specification
│   └── topics/                # Conceptual deep-dives
├── src/acap/types/            # Pydantic type library (Python)
│   ├── policy_document.py     # PolicyDocument, PolicyClaim, UsagePolicyRef
│   ├── consent_record.py      # ConsentRecord, ParsedClaim
│   └── adherence_event.py     # AdherenceEvent, CheckAdherence*
├── samples/python/            # Reference agent.json with usage_policy
└── adrs/                      # Architecture Decision Records
    ├── 001-usage-policy-as-agent-card-extension.md
    └── 002-proof-of-adherence-over-proof-of-acceptance.md
```

## Formal Verification

The protocol's core safety properties (chain integrity, consent-before-action,
version-gated re-acceptance) are specified in TLA+ and verified with the TLC
model checker. TLC exhaustively explores the state space within declared
constants (e.g. `MaxAgents`, `MaxVersions`) but does **not** constitute a
proof for arbitrary values. Unbounded verification would require a theorem
prover such as TLAPS.

The TLA+ specification is described in the companion paper
([Anumati](https://arxiv.org/abs/2503.XXXXX), §5).

## Contributing

Contributions are welcome. Please use GitHub Issues for proposals and bug
reports, and GitHub Discussions for questions. This project follows the
[A2A](https://github.com/a2aproject/A2A) contribution model.

## License

Apache 2.0. See [LICENSE](LICENSE).
