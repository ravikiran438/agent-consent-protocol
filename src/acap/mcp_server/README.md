# ACAP MCP Server

A reference [Model Context Protocol](https://modelcontextprotocol.io/)
server that exposes ACAP Core validators and the four extension entry
points as MCP tools. Uses stdio transport. Works with any
MCP-compatible client; see the VSCode section below for one concrete
configuration.

## Install

From the repository root:

```bash
pip install -e '.[mcp]'
```

This installs the MCP Python SDK alongside the ACAP package and
registers the `acap-mcp` console script.

## Run

```bash
acap-mcp          # from the install, uses stdio transport
```

Or without the script wrapper:

```bash
python -m acap.mcp_server
```

The server writes MCP protocol messages on stdout and reads requests
on stdin. It is not interactive from a shell; an MCP client starts it
as a subprocess.

## Tools exposed

| Tool | Purpose |
|---|---|
| `validate_consent_chain` | Validate a consent chain (linkage, pair consistency, per-claim coverage, hash match when policies are supplied). |
| `validate_adherence_trail` | Validate an adherence trail anchored against a consent chain. |
| `compute_policy_hash` | Canonical SHA-256 hash for a PolicyDocument. |
| `classify_policy_bump` | Governance-tiering: diff two PolicyDocument versions and return tier + assessment. |
| `resolve_sensitivity` | Category-preferences: resolve a (category, dimension) cell. |
| `compute_floor` | Regulatory-context: strictest floor across principal preferences + all declared contexts. |
| `generate_audit_report` | Audit-projection: walk chain + trail and return a structured report. |
| `validate_audit_report` | Audit-projection: verify structural invariants of a projection. |

All tools take and return JSON. See `src/acap/mcp_server/tools.py` for
input schemas and output shapes.

## Wire into VSCode

Add this to `.vscode/mcp.json` at your workspace root (or configure
globally via your VSCode user settings, under the MCP section):

```json
{
  "servers": {
    "acap": {
      "type": "stdio",
      "command": "/absolute/path/to/your/.venv/bin/acap-mcp"
    }
  }
}
```

Reload the workspace. The tools appear in any MCP-aware VSCode
extension under the `acap` server name.

## Sample payloads

See [`EXAMPLES.md`](./EXAMPLES.md) for ready-to-paste JSON per tool,
covering the happy path and the failure variant for each one.

## Doctor check

Run a structural self-check (tool registry intact, schemas
well-formed) without spawning the stdio loop:

```bash
acap-mcp --doctor
```

Exit code is 0 when all tools register correctly, 1 otherwise.
Suitable for CI as a quick "did my install work?" gate.

## Testing

```bash
pytest tests/mcp_server/
```

Tool handlers are tested directly (not through the stdio loop), which
keeps the tests fast and focused on the JSON contract. One stdio
smoke test spawns the server as a subprocess and completes the
handshake end-to-end.
