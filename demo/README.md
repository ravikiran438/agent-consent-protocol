# ACAP Demo: A2A + Gemini

An end-to-end demonstration that the Anumati consent model deploys as a
middleware layer against A2A without changes to the core protocol.
Two agents, both driven by Gemini 2.5 Flash, negotiate a consent
handshake and then exchange a skill call gated by per-action adherence
evaluation.

## What it shows

1. The callee publishes an A2A AgentCard at
   `/.well-known/agent-card.json` with the ACAP extension declared in
   `capabilities.extensions` and a top-level `usage_policy` pointer.
2. The caller fetches the policy, verifies its `document_hash` against
   the canonical hash computed from the document body (§3.1 of the
   paper), and asks Gemini to parse each `PolicyClaim` into a
   `ParsedClaim`.
3. The caller submits a `ConsentRecord` to `/acap/consent`.
4. Before each skill invocation, the caller records an
   `AdherenceEvent` to `/acap/adherence`. The first call carries a
   purpose that matches the policy's prohibition constraint and is
   blocked; the second carries a permitted purpose and succeeds.
5. The callee serves `/acap/audit/<caller_agent_id>` with the full
   chain + trail.

## Prerequisites

- Python 3.12 or 3.13
- A Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- The `acap` package installed with the `demo` optional dependencies

## Setup

```bash
cp .env.example .env
# put your GOOGLE_API_KEY in .env

python -m venv .venv
source .venv/bin/activate
pip install -e ".[demo]"
```

## Run

Open two terminals.

**Terminal 1 (callee):**

```bash
uvicorn demo.callee_agent:app --host 127.0.0.1 --port 8001
```

**Terminal 2 (caller):**

```bash
python -m demo.caller_agent
```

The caller prints a four-section trace: the consent handshake, the
blocked skill call, the permitted skill call, and the audit report.

## What to read in the code

| File | Role |
|---|---|
| [`src/acap/middleware/caller.py`](../src/acap/middleware/caller.py) | Pluggable `ACAPCaller` with a `ClaimParser` protocol; ships with a `GeminiClaimParser` |
| [`src/acap/middleware/callee.py`](../src/acap/middleware/callee.py) | `ACAPCallee` in-memory store + `build_fastapi_router` for the two HTTP endpoints |
| [`demo/callee_agent.py`](callee_agent.py) | FastAPI app with AgentCard, policy, one skill gated by `ACAPCallee.require_permit` |
| [`demo/caller_agent.py`](caller_agent.py) | Async script that walks the handshake + skill call + audit |

## Notes on the demo scope

- Storage is in-memory. A production callee would append consent
  records and adherence events to a durable store and expose the
  audit trail over signed reads.
- JWS signatures are not computed. The paper's §6.1 calls this out;
  the reference validators accept signature-less records.
- Network is local. The wall-clock latency numbers reported in §4.3
  of the paper are measured in-process; end-to-end latency over the
  loopback interface is dominated by HTTP overhead, not ACAP.
