# Agent Consent and Adherence Protocol — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/agent-consent-protocol/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina
- **Paper / human-readable spec:** https://doi.org/10.5281/zenodo.19606339

Versioned, machine-readable usage-policy adherence layer for A2A agents.

## AgentCard payload

**Required fields:** `acceptance_required`, `document_hash`, `document_uri`, `effective_date`, `natural_language_uri`, `version`

| Field | Type | Required | Notes |
|---|---|---|---|
| `acceptance_endpoint` | any | no | HTTPS endpoint at which callers POST a ConsentRecord. REQUIRED when acceptance_required is true. |
| `acceptance_required` | boolean | yes | Whether callers MUST complete the ACAP consent handshake before invoking any skill. |
| `change_summary` | any | no | One-line summary of material changes for agent reasoning. |
| `document_hash` | string | yes | SHA-256 hex digest of the current PolicyDocument. Format: 'sha256:<hex>'. |
| `document_uri` | string | yes | HTTPS URL where the PolicyDocument JSON is hosted. |
| `effective_date` | string | yes | ISO 8601 UTC datetime from which this version is effective. |
| `natural_language_uri` | string | yes | HTTPS URL of the human-readable Terms of Service. |
| `supersedes` | any | no | Semver of the previous PolicyDocument version. |
| `version` | string | yes | Semver of the current PolicyDocument. |

## Invariants

- Records form an append-only linked chain per agent-pair per policy version.
- Caller MUST parse every PolicyClaim before invoking any skill.

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
