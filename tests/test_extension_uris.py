# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Lock-in tests for ACAP's published extension URIs.

Each URI is normative — flipping it breaks deployed AgentCards. These
tests fail loudly if the constants are renamed or moved without an
explicit version bump.
"""

from __future__ import annotations


def test_acap_core_extension_uri():
    from acap.types import ACAP_EXTENSION_URI
    assert ACAP_EXTENSION_URI == (
        "https://ravikiran438.github.io/agent-consent-protocol/v1"
    )


def test_governance_tiering_extension_uri():
    from acap.extensions.governance_tiering import EXTENSION_URI
    assert EXTENSION_URI == (
        "https://github.com/ravikiran438/agent-consent-protocol/"
        "extensions/governance-tiering/v1"
    )


def test_category_preferences_extension_uri():
    from acap.extensions.category_preferences import EXTENSION_URI
    assert EXTENSION_URI == (
        "https://github.com/ravikiran438/agent-consent-protocol/"
        "extensions/category-preferences/v1"
    )


def test_regulatory_context_extension_uri():
    from acap.extensions.regulatory_context import EXTENSION_URI
    assert EXTENSION_URI == (
        "https://github.com/ravikiran438/agent-consent-protocol/"
        "extensions/regulatory-context/v1"
    )


def test_audit_projection_extension_uri():
    from acap.extensions.audit_projection import EXTENSION_URI
    assert EXTENSION_URI == (
        "https://github.com/ravikiran438/agent-consent-protocol/"
        "extensions/audit-projection/v1"
    )
