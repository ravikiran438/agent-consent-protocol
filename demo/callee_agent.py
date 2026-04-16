# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Demo callee agent: a data-analysis service that publishes an ACAP
usage policy and gates its skill behind the consent + adherence
handshake.

Run with:
    uvicorn demo.callee_agent:app --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from pydantic import BaseModel

from acap.middleware import ACAPCallee, build_fastapi_router
from acap.types import PolicyClaim, PolicyDocument, RuleType
from acap.validators.hash import compute_policy_hash


load_dotenv()

CALLEE_BASE_URL = "http://127.0.0.1:8001"
CALLEE_AGENT_ID = "did:agent:data-analysis-agent"

# ──────────────────────────────────────────────────────────────────────
# Build the PolicyDocument this callee advertises.
# ──────────────────────────────────────────────────────────────────────

_POLICY_CLAIMS = [
    PolicyClaim(
        claim_id="claim-retention",
        clause_ref="§2.1",
        action="odrl:store",
        asset="pii:session_data",
        rule_type=RuleType.PROHIBITION,
        constraint="odrl:elapsedTime is past_session",
        effective_version="1.0.0",
    ),
    PolicyClaim(
        claim_id="claim-aggregation-prohibition",
        clause_ref="§3.4",
        action="odrl:aggregate",
        asset="pii:session_data",
        rule_type=RuleType.PROHIBITION,
        constraint="odrl:purpose is behavioural_profiling",
        effective_version="1.0.0",
    ),
    PolicyClaim(
        claim_id="claim-no-third-party",
        clause_ref="§5.2",
        action="odrl:distribute",
        asset="pii:session_data",
        rule_type=RuleType.PROHIBITION,
        constraint=None,
        effective_version="1.0.0",
    ),
]


def _build_policy() -> PolicyDocument:
    policy = PolicyDocument(
        version="1.0.0",
        document_uri=f"{CALLEE_BASE_URL}/.well-known/usage-policy.json",
        document_hash="sha256:placeholder",
        effective_date="2026-04-01T00:00:00Z",
        claims=_POLICY_CLAIMS,
        publisher=CALLEE_AGENT_ID,
        natural_language_uri=f"{CALLEE_BASE_URL}/terms",
        jurisdictions=["EU AI Act"],
    )
    policy.document_hash = compute_policy_hash(policy)
    return policy


POLICY = _build_policy()
CALLEE = ACAPCallee(policy=POLICY)


# ──────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="data-analysis-agent")
app.include_router(build_fastapi_router(CALLEE))


@app.get("/.well-known/agent-card.json")
def agent_card() -> dict:
    """Standard A2A AgentCard + ACAP extension."""
    return {
        "name": "data-analysis-agent",
        "description": "Aggregates and analyses customer session datasets.",
        "url": CALLEE_BASE_URL,
        "capabilities": {
            "extensions": [
                {
                    "uri": "https://github.com/ravikiran438/agent-consent-protocol/v0.1",
                    "description": "Supports the Agent Consent and Adherence Protocol.",
                    "required": True,
                }
            ]
        },
        "skills": [
            {
                "name": "analyse_dataset",
                "description": "Runs aggregate statistics over a customer dataset.",
                "policy_claims": [
                    "claim-aggregation-prohibition",
                    "claim-retention",
                ],
            }
        ],
        "usage_policy": {
            "version": POLICY.version,
            "document_uri": POLICY.document_uri,
            "document_hash": POLICY.document_hash,
            "effective_date": POLICY.effective_date,
            "acceptance_required": True,
            "acceptance_endpoint": f"{CALLEE_BASE_URL}/acap/consent",
            "natural_language_uri": POLICY.natural_language_uri,
            "publisher": POLICY.publisher,
        },
    }


@app.get("/.well-known/usage-policy.json")
def usage_policy() -> dict:
    return POLICY.model_dump(mode="json")


# ──────────────────────────────────────────────────────────────────────
# The actual skill, gated by the ACAP handshake + adherence
# ──────────────────────────────────────────────────────────────────────


class AnalyseDatasetRequest(BaseModel):
    caller_agent_id: str
    csv_url: str
    purpose: str


@dataclass
class _Summariser:
    model: str = "gemini-2.5-flash"

    def __post_init__(self) -> None:
        if not os.environ.get("GOOGLE_API_KEY"):
            raise RuntimeError(
                "GOOGLE_API_KEY not set: the demo callee needs it to run "
                "Gemini-backed analysis"
            )
        self._client = genai.Client()

    def run(self, csv_url: str, purpose: str) -> str:
        prompt = (
            f"You are an analytics agent. The calling agent has obtained "
            f"consent to run analysis on a customer dataset for the stated "
            f"purpose {purpose!r}. Pretend the dataset at {csv_url} contains "
            "100 rows of (user_id, session_duration_seconds, page_views). "
            "Produce a two-sentence high-level summary of what the aggregate "
            "statistics would look like. Do not invent specific numbers, "
            "speak in qualitative terms."
        )
        resp = self._client.models.generate_content(
            model=self.model, contents=prompt
        )
        return resp.text.strip()


_summariser = _Summariser()


@app.post("/skills/analyse_dataset")
def analyse_dataset(req: AnalyseDatasetRequest) -> dict:
    # Gate #1: consent must exist + be accepted/conditional.
    # Gate #2: latest AdherenceEvent for the governing claim must be permit.
    permit = CALLEE.require_permit(
        caller_agent_id=req.caller_agent_id,
        claim_id="claim-aggregation-prohibition",
    )

    summary = _summariser.run(req.csv_url, req.purpose)

    return {
        "summary": summary,
        "authorised_by_event_id": permit.event_id,
    }
