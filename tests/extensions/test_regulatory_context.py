# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for the regulatory-context extension.

These tests exercise the ENVELOPE: the floor-computation lattice, the
composition across principal/callee/caller sources, and the structural
validator. They deliberately use obligation references like
'HYPOTHETICAL-X' and descriptions like 'test obligation' so that the
tests cannot be mis-read as a normative mapping of any real regulation.

The real regulatory mappings (HIPAA, GDPR, PCI-DSS, EU AI Act, ...)
require qualified legal review and are explicitly out of scope for
this reference implementation.
"""

from __future__ import annotations

import pytest

from acap.extensions.category_preferences import (
    CategoryPreference,
    CategorySensitivity,
    DataCategory,
    UsageDimension,
)
from acap.extensions.regulatory_context import (
    ComplianceObligation,
    RegulatoryContext,
    RegulatoryContextValidationError,
    RegulatoryFramework,
    compute_floor,
    max_sensitivity,
    validate_regulatory_context,
)


def _obligation(
    ref: str,
    categories: list[DataCategory],
    dimensions: list[UsageDimension],
    minimum: CategorySensitivity,
    description: str = "test obligation (hypothetical)",
) -> ComplianceObligation:
    return ComplianceObligation(
        obligation_ref=ref,
        affected_categories=categories,
        affected_dimensions=dimensions,
        minimum_sensitivity=minimum,
        description=description,
    )


def _context(
    framework: RegulatoryFramework,
    role: str,
    obligations: list[ComplianceObligation],
    always_notify: bool = False,
) -> RegulatoryContext:
    return RegulatoryContext(
        framework=framework,
        role=role,
        obligations=obligations,
        always_notify_principal=always_notify,
    )


# ─────────────────────────────────────────────────────────────────────────────
# max_sensitivity
# ─────────────────────────────────────────────────────────────────────────────


def test_max_sensitivity_ordering():
    L, M, H = (
        CategorySensitivity.LOW,
        CategorySensitivity.MEDIUM,
        CategorySensitivity.HIGH,
    )
    assert max_sensitivity(L, M) is M
    assert max_sensitivity(M, L) is M
    assert max_sensitivity(M, H) is H
    assert max_sensitivity(H, L) is H
    assert max_sensitivity(L, L) is L
    assert max_sensitivity(H, H) is H


# ─────────────────────────────────────────────────────────────────────────────
# compute_floor
# ─────────────────────────────────────────────────────────────────────────────


def test_floor_with_no_preferences_and_no_contexts_is_low():
    assert (
        compute_floor([], [], DataCategory.HEALTH, UsageDimension.STORAGE)
        is CategorySensitivity.LOW
    )


def test_floor_uses_principal_preference_when_no_contexts():
    prefs = [
        CategoryPreference(
            category=DataCategory.HEALTH,
            sensitivity=CategorySensitivity.MEDIUM,
        )
    ]
    assert (
        compute_floor(prefs, [], DataCategory.HEALTH, UsageDimension.STORAGE)
        is CategorySensitivity.MEDIUM
    )


def test_floor_uses_context_when_no_principal_preference():
    ctx = _context(
        RegulatoryFramework.HIPAA,
        "covered_entity",
        [
            _obligation(
                "HYPOTHETICAL-1",
                [DataCategory.HEALTH],
                [UsageDimension.STORAGE],
                CategorySensitivity.HIGH,
            )
        ],
    )
    assert (
        compute_floor([], [ctx], DataCategory.HEALTH, UsageDimension.STORAGE)
        is CategorySensitivity.HIGH
    )


def test_floor_takes_strictest_of_principal_and_context():
    # Principal is relaxed (LOW), context demands HIGH. Floor = HIGH.
    prefs = [
        CategoryPreference(
            category=DataCategory.HEALTH,
            sensitivity=CategorySensitivity.LOW,
        )
    ]
    ctx = _context(
        RegulatoryFramework.HIPAA,
        "covered_entity",
        [
            _obligation(
                "HYPOTHETICAL-2",
                [DataCategory.HEALTH],
                [UsageDimension.THIRD_PARTY_SHARING],
                CategorySensitivity.HIGH,
            )
        ],
    )
    assert (
        compute_floor(
            prefs, [ctx], DataCategory.HEALTH, UsageDimension.THIRD_PARTY_SHARING
        )
        is CategorySensitivity.HIGH
    )


def test_floor_principal_stricter_than_context_is_honored():
    # Principal is HIGH, context is MEDIUM. Floor stays at HIGH.
    prefs = [
        CategoryPreference(
            category=DataCategory.BIOMETRIC,
            sensitivity=CategorySensitivity.HIGH,
        )
    ]
    ctx = _context(
        RegulatoryFramework.GDPR,
        "data_controller",
        [
            _obligation(
                "HYPOTHETICAL-3",
                [DataCategory.BIOMETRIC],
                [UsageDimension.STORAGE],
                CategorySensitivity.MEDIUM,
            )
        ],
    )
    assert (
        compute_floor(
            prefs, [ctx], DataCategory.BIOMETRIC, UsageDimension.STORAGE
        )
        is CategorySensitivity.HIGH
    )


def test_floor_takes_strictest_across_multiple_contexts():
    # Two contexts: one demands MEDIUM, one demands HIGH, for the same cell.
    ctx_a = _context(
        RegulatoryFramework.HIPAA,
        "covered_entity",
        [
            _obligation(
                "HYPOTHETICAL-4a",
                [DataCategory.HEALTH],
                [UsageDimension.ACCESS],
                CategorySensitivity.MEDIUM,
            )
        ],
    )
    ctx_b = _context(
        RegulatoryFramework.EU_AI_ACT,
        "deployer",
        [
            _obligation(
                "HYPOTHETICAL-4b",
                [DataCategory.HEALTH],
                [UsageDimension.ACCESS],
                CategorySensitivity.HIGH,
            )
        ],
    )
    assert (
        compute_floor(
            [], [ctx_a, ctx_b], DataCategory.HEALTH, UsageDimension.ACCESS
        )
        is CategorySensitivity.HIGH
    )


def test_floor_ignores_obligations_for_other_categories():
    ctx = _context(
        RegulatoryFramework.HIPAA,
        "covered_entity",
        [
            _obligation(
                "HYPOTHETICAL-5",
                [DataCategory.HEALTH],
                [UsageDimension.STORAGE],
                CategorySensitivity.HIGH,
            )
        ],
    )
    # Query is on FINANCIAL, not HEALTH, so the HIPAA floor does not apply.
    assert (
        compute_floor(
            [], [ctx], DataCategory.FINANCIAL, UsageDimension.STORAGE
        )
        is CategorySensitivity.LOW
    )


def test_floor_ignores_obligations_for_other_dimensions():
    ctx = _context(
        RegulatoryFramework.HIPAA,
        "covered_entity",
        [
            _obligation(
                "HYPOTHETICAL-6",
                [DataCategory.HEALTH],
                [UsageDimension.THIRD_PARTY_SHARING],
                CategorySensitivity.HIGH,
            )
        ],
    )
    # Query is on STORAGE; the obligation only constrains THIRD_PARTY_SHARING.
    assert (
        compute_floor([], [ctx], DataCategory.HEALTH, UsageDimension.STORAGE)
        is CategorySensitivity.LOW
    )


def test_floor_obligation_applies_to_all_cross_product_cells():
    # One obligation, two categories, two dimensions. Covers all four cells.
    ctx = _context(
        RegulatoryFramework.GDPR,
        "data_controller",
        [
            _obligation(
                "HYPOTHETICAL-7",
                [DataCategory.HEALTH, DataCategory.BIOMETRIC],
                [UsageDimension.STORAGE, UsageDimension.THIRD_PARTY_SHARING],
                CategorySensitivity.MEDIUM,
            )
        ],
    )
    for cat in (DataCategory.HEALTH, DataCategory.BIOMETRIC):
        for dim in (UsageDimension.STORAGE, UsageDimension.THIRD_PARTY_SHARING):
            assert (
                compute_floor([], [ctx], cat, dim) is CategorySensitivity.MEDIUM
            )


# ─────────────────────────────────────────────────────────────────────────────
# validate_regulatory_context
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_accepts_well_formed_context():
    validate_regulatory_context(
        _context(
            RegulatoryFramework.HIPAA,
            "covered_entity",
            [
                _obligation(
                    "HYPOTHETICAL-OK",
                    [DataCategory.HEALTH],
                    [UsageDimension.STORAGE],
                    CategorySensitivity.HIGH,
                )
            ],
        )
    )


def test_validate_rejects_empty_role():
    ctx = _context(
        RegulatoryFramework.HIPAA,
        "   ",  # whitespace
        [
            _obligation(
                "HYPOTHETICAL-8",
                [DataCategory.HEALTH],
                [UsageDimension.STORAGE],
                CategorySensitivity.HIGH,
            )
        ],
    )
    with pytest.raises(RegulatoryContextValidationError, match="empty role"):
        validate_regulatory_context(ctx)


def test_validate_rejects_duplicate_obligation_ref():
    ctx = _context(
        RegulatoryFramework.GDPR,
        "data_controller",
        [
            _obligation(
                "HYPOTHETICAL-DUP",
                [DataCategory.HEALTH],
                [UsageDimension.STORAGE],
                CategorySensitivity.MEDIUM,
            ),
            _obligation(
                "HYPOTHETICAL-DUP",
                [DataCategory.IDENTITY],
                [UsageDimension.ACCESS],
                CategorySensitivity.HIGH,
            ),
        ],
    )
    with pytest.raises(RegulatoryContextValidationError, match="duplicate"):
        validate_regulatory_context(ctx)


def test_validate_rejects_empty_obligation_ref():
    ctx = _context(
        RegulatoryFramework.HIPAA,
        "covered_entity",
        [
            _obligation(
                "",  # empty
                [DataCategory.HEALTH],
                [UsageDimension.STORAGE],
                CategorySensitivity.HIGH,
            )
        ],
    )
    with pytest.raises(
        RegulatoryContextValidationError, match="empty obligation_ref"
    ):
        validate_regulatory_context(ctx)


def test_validate_rejects_whitespace_only_obligation_ref():
    ctx = _context(
        RegulatoryFramework.HIPAA,
        "covered_entity",
        [
            _obligation(
                "   ",
                [DataCategory.HEALTH],
                [UsageDimension.STORAGE],
                CategorySensitivity.HIGH,
            )
        ],
    )
    with pytest.raises(
        RegulatoryContextValidationError, match="empty obligation_ref"
    ):
        validate_regulatory_context(ctx)


def test_always_notify_principal_flag_accepted():
    ctx = _context(
        RegulatoryFramework.EU_AI_ACT,
        "deployer",
        [
            _obligation(
                "HYPOTHETICAL-9",
                [DataCategory.IDENTITY],
                [UsageDimension.AUTOMATED_DECISION],
                CategorySensitivity.HIGH,
            )
        ],
        always_notify=True,
    )
    validate_regulatory_context(ctx)
    assert ctx.always_notify_principal is True
