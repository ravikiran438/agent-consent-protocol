# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Demo caller agent: a marketing-insights agent that wants to use the
data-analysis callee. Walks through the ACAP consent handshake, then
runs two skill calls, one with a purpose that the callee's policy
disallows (blocked at the adherence layer) and one with a permitted
purpose (runs successfully).

Run with:
    python -m demo.caller_agent

The callee_agent must be running at CALLEE_BASE_URL first.
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx
from dotenv import load_dotenv

from acap.middleware.caller import ACAPCaller, GeminiClaimParser


load_dotenv()

CALLER_AGENT_ID = "did:agent:marketing-insights"
PRINCIPAL_ID = "principal:ravi@example.com"
CALLEE_BASE_URL = "http://127.0.0.1:8001"


def _hr(title: str) -> None:
    print("\n" + "─" * 72)
    print(title)
    print("─" * 72)


async def main() -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise SystemExit(
            "GOOGLE_API_KEY is not set. Put it in .env at the repo root."
        )

    _hr("1. Consent handshake")

    caller = ACAPCaller(
        caller_agent_id=CALLER_AGENT_ID,
        principal_id=PRINCIPAL_ID,
        caller_intent=(
            "Produce a marketing insights report for the current quarter. "
            "The report will not be used for behavioural profiling of "
            "individual customers."
        ),
        claim_parser=GeminiClaimParser(model="gemini-2.5-flash"),
    )

    try:
        record = await caller.bind(CALLEE_BASE_URL)
        print(f"ConsentRecord id      : {record.record_id}")
        print(f"Decision              : {record.decision.value}")
        for parsed in record.parsed_claims:
            print(
                f"  - {parsed.claim_id:<32s} understood={parsed.understood}"
                f"  disputed={parsed.disputed}"
            )
            if parsed.disputed and parsed.dispute_reason:
                print(f"      dispute_reason: {parsed.dispute_reason}")

        _hr("2. First skill call: purpose = behavioural_profiling (expect deny)")

        evt1 = await caller.check_and_record(
            callee_base_url=CALLEE_BASE_URL,
            action="odrl:aggregate",
            claim_id="claim-aggregation-prohibition",
            clause_evaluated="§3.4",
            context={"purpose": "behavioural_profiling"},
        )
        print(f"AdherenceEvent id     : {evt1.event_id}")
        print(f"Decision              : {evt1.decision.value}")
        print(f"Reasoning             : {evt1.reasoning}")

        if evt1.decision.value == "permit":
            await _call_skill(caller.http, "behavioural_profiling")
        else:
            print("Caller will NOT invoke the skill; as expected, the "
                  "adherence layer blocked the call.")

        _hr("3. Second skill call: purpose = statistical_analysis (expect permit)")

        evt2 = await caller.check_and_record(
            callee_base_url=CALLEE_BASE_URL,
            action="odrl:aggregate",
            claim_id="claim-aggregation-prohibition",
            clause_evaluated="§3.4",
            context={"purpose": "statistical_analysis"},
        )
        print(f"AdherenceEvent id     : {evt2.event_id}")
        print(f"Decision              : {evt2.decision.value}")
        print(f"Reasoning             : {evt2.reasoning}")

        if evt2.decision.value == "permit":
            result = await _call_skill(caller.http, "statistical_analysis")
            print("\nSkill result:")
            print(f"  summary      : {result['summary']}")
            print(f"  authorised_by: {result['authorised_by_event_id']}")

        _hr("4. Audit report fetched from the callee")

        audit_resp = await caller.http.get(
            f"{CALLEE_BASE_URL}/acap/audit/{CALLER_AGENT_ID}"
        )
        audit = audit_resp.json()
        print(json.dumps(audit, indent=2, ensure_ascii=False)[:1800])
        print("...")

    finally:
        await caller.aclose()


async def _call_skill(client: httpx.AsyncClient, purpose: str) -> dict:
    resp = await client.post(
        f"{CALLEE_BASE_URL}/skills/analyse_dataset",
        json={
            "caller_agent_id": CALLER_AGENT_ID,
            "csv_url": "s3://demo/customer_sessions_q1_2026.csv",
            "purpose": purpose,
        },
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    asyncio.run(main())
