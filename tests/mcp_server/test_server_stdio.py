# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""End-to-end stdio smoke test for the ACAP MCP server.

Spawns the server as a subprocess, issues the MCP handshake via the
official client SDK, lists tools, and calls one. Confirms the
registration, transport, and call plumbing work together.
"""

from __future__ import annotations

import json
import sys

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_server_lists_tools_over_stdio():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "acap.mcp_server"],
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    names = {t.name for t in tools.tools}
    expected = {
        "validate_consent_chain",
        "validate_adherence_trail",
        "compute_policy_hash",
        "classify_policy_bump",
        "resolve_sensitivity",
        "compute_floor",
        "generate_audit_report",
        "validate_audit_report",
        "validate_usage_policy_ref",
    }
    assert names == expected


@pytest.mark.asyncio
async def test_server_call_compute_policy_hash_over_stdio():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "acap.mcp_server"],
    )

    policy = {
        "version": "1.0.0",
        "document_uri": "https://example.com/p.json",
        "document_hash": "sha256:" + "0" * 64,
        "effective_date": "2026-03-01T00:00:00Z",
        "claims": [
            {
                "claim_id": "a",
                "clause_ref": "§a",
                "action": "odrl:aggregate",
                "asset": "pii:session_data",
                "rule_type": "prohibition",
                "effective_version": "1.0.0",
            }
        ],
        "publisher": "https://example.com",
        "natural_language_uri": "https://example.com/terms",
    }

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "compute_policy_hash", {"policy": policy}
            )

    assert result.content, "tool returned no content"
    body = json.loads(result.content[0].text)
    assert body["ok"] is True
    assert body["hash"].startswith("sha256:")
    assert len(body["hash"]) == len("sha256:") + 64
