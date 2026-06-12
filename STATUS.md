# ACAP — repository status

Snapshot of where this repo stands; written so future-me can re-page-in
without trawling git logs.

## Last touched

May 1, 2026 — added `validate_usage_policy_ref` MCP tool, regression
tests for `EXTENSION_URI` constants, and a v1 manifest.

## What works (verified)

- 146 tests passing locally via the shared venv at `../../.venv` (incl. the
  AG-UI binding suite; in a bare sandbox the 2 `mcp_server` stdio tests are
  skipped/fail for lack of a stdio peer — unrelated to the protocol).
- **AG-UI binding** at `acap.ag_ui` (`src/acap/ag_ui/binding.py`): projects
  ACAP's two human-in-the-loop moments onto the agent↔human transport — the
  consent gate (`PolicyDocument` snapshot → `confirmation`/`tool_call` interrupt
  → typed `ConsentRecord`) and per-action adherence (routine `AdherenceEvent`s
  as `Custom`; an `escalate` becomes an interrupt → typed `AdherenceEvent`,
  fail-closed to deny). Dependency-free; 13 tests in
  `tests/test_ag_ui_binding.py`. Follows the cross-cutting *Governance over
  AG-UI* spec (<https://ravikiran438.github.io/agent-protocol-stack/ag-ui/>).
- TLA+ model `specification/ConsentLifecycle.tla` checks clean under
  TLC (~4.4M states, depth 17, no invariant violations).
- MCP server at `acap.mcp_server` exposes 9 validator tools including
  the new `validate_usage_policy_ref`.
- ExtensionManifest published at `v1/manifest.json` (auto-generated
  from `acap.types.UsagePolicyRef`).
- 4 sub-extension manifests at `extensions/<name>/v1/manifest.json`
  (governance-tiering, category-preferences, regulatory-context,
  audit-projection).
- All `EXTENSION_URI` constants locked by `tests/test_extension_uris.py`.

## What's pending

- Repo not yet pushed to GitHub. Phase 2 commit + push is owed.
- Once pushed, GitHub Pages will need to be enabled if the URI
  strategy switches from `github.com/...` to `ravikiran438.github.io/...`
  (decision lives in the testbed's MASTER_STATUS.md).
- ACAP preprint (current published v4 at Zenodo DOI .19606339) does
  NOT need a v5 from this round — no core wire-format changes were
  applied. The 4 sub-extensions remain "URI declared, schema mostly
  opaque" until each gets a substantive design pass.

## Re-page-in checklist (if returning after 2+ weeks)

1. `cd <here> && ../../.venv/bin/python -m pytest -q` — should be 146/146.
2. `java -Xmx4g -cp "$TLA2TOOLS" tlc2.TLC -workers auto -deadlock ConsentLifecycle`
   from `specification/`. Expect "no error" (~4M states).
3. Re-read `MASTER_STATUS.md` in the testbed for cross-repo context.
4. Check `git log --oneline` for anything I touched without updating
   this file.

## Files I'd look at first

- `src/acap/types/policy_document.py` — `UsagePolicyRef` is the
  AgentCard descriptor; it's the source of truth for the v1 manifest.
- `src/acap/mcp_server/tools.py` — MCP tool registry; adding a new
  validator follows the patterns at the bottom of the file.
- `v1/manifest.json` — keep aligned with `UsagePolicyRef` via
  `a2a-testbed manifest generate`.

## Known gaps / future work

- 4 sub-extensions have URIs and OpaquePayload manifests but minimal
  semantic implementations. Each was scaffolded as a placeholder for
  a future paper revision.
- `validate_usage_policy_ref` checks structural shape + the
  `acceptance_required` ↔ `acceptance_endpoint` coherence, but does
  not fetch and validate the referenced PolicyDocument. That belongs
  to a richer runtime check, possibly in a different tool.
