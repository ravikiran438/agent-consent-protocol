# ACAP Category-Preferences Extension — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/agent-consent-protocol/extensions/category-preferences/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina

Per-category sensitivity preferences for human principals.

## AgentCard payload

This extension declares itself by URI presence and does not constrain the AgentCard payload. Validators accept any object in the entry's `params`.

## Invariants

- Each DataCategory has at most one declared sensitivity per principal.

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
