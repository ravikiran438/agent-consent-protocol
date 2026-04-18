# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for the category-preferences extension.

Covers matrix resolution (default-row fallback, specific-cell override,
absence default) and the uniqueness validator.
"""

from __future__ import annotations

import pytest

from acap.extensions.category_preferences import (
    CategoryPreference,
    CategoryPreferencesValidationError,
    CategorySensitivity,
    DataCategory,
    UsageDimension,
    resolve_sensitivity,
    validate_preferences,
)


def _pref(
    category: DataCategory,
    sensitivity: CategorySensitivity,
    dimension: UsageDimension | None = None,
    note: str | None = None,
) -> CategoryPreference:
    return CategoryPreference(
        category=category,
        sensitivity=sensitivity,
        dimension=dimension,
        note=note,
    )


# ─────────────────────────────────────────────────────────────────────────────
# resolve_sensitivity
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_specific_cell_wins():
    prefs = [
        _pref(DataCategory.BIOMETRIC, CategorySensitivity.HIGH),
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.LOW,
            dimension=UsageDimension.ACCESS,
        ),
    ]
    # ACCESS has an explicit LOW override, wins over the HIGH default row.
    assert (
        resolve_sensitivity(prefs, DataCategory.BIOMETRIC, UsageDimension.ACCESS)
        is CategorySensitivity.LOW
    )


def test_resolve_default_row_applies_when_no_specific_cell():
    prefs = [_pref(DataCategory.BIOMETRIC, CategorySensitivity.HIGH)]
    assert (
        resolve_sensitivity(prefs, DataCategory.BIOMETRIC, UsageDimension.STORAGE)
        is CategorySensitivity.HIGH
    )


def test_resolve_returns_low_when_no_matching_category():
    prefs = [_pref(DataCategory.BIOMETRIC, CategorySensitivity.HIGH)]
    assert (
        resolve_sensitivity(prefs, DataCategory.HEALTH, UsageDimension.STORAGE)
        is CategorySensitivity.LOW
    )


def test_resolve_returns_low_on_empty_preferences():
    assert (
        resolve_sensitivity([], DataCategory.BIOMETRIC, UsageDimension.STORAGE)
        is CategorySensitivity.LOW
    )


def test_resolve_multiple_categories_independent():
    prefs = [
        _pref(DataCategory.HEALTH, CategorySensitivity.MEDIUM),
        _pref(DataCategory.FINANCIAL, CategorySensitivity.HIGH),
    ]
    assert (
        resolve_sensitivity(prefs, DataCategory.HEALTH, UsageDimension.ACCESS)
        is CategorySensitivity.MEDIUM
    )
    assert (
        resolve_sensitivity(
            prefs, DataCategory.FINANCIAL, UsageDimension.THIRD_PARTY_SHARING
        )
        is CategorySensitivity.HIGH
    )


def test_resolve_specific_cell_regardless_of_list_order():
    # specific cell appears before the default row
    prefs = [
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.LOW,
            dimension=UsageDimension.ACCESS,
        ),
        _pref(DataCategory.BIOMETRIC, CategorySensitivity.HIGH),
    ]
    assert (
        resolve_sensitivity(prefs, DataCategory.BIOMETRIC, UsageDimension.ACCESS)
        is CategorySensitivity.LOW
    )
    assert (
        resolve_sensitivity(prefs, DataCategory.BIOMETRIC, UsageDimension.STORAGE)
        is CategorySensitivity.HIGH
    )


# ─────────────────────────────────────────────────────────────────────────────
# validate_preferences
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_accepts_empty_list():
    validate_preferences([])


def test_validate_accepts_non_overlapping_entries():
    validate_preferences([
        _pref(DataCategory.BIOMETRIC, CategorySensitivity.HIGH),
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.LOW,
            dimension=UsageDimension.ACCESS,
        ),
        _pref(DataCategory.HEALTH, CategorySensitivity.MEDIUM),
    ])


def test_validate_rejects_duplicate_default_row():
    prefs = [
        _pref(DataCategory.BIOMETRIC, CategorySensitivity.HIGH),
        _pref(DataCategory.BIOMETRIC, CategorySensitivity.LOW),
    ]
    with pytest.raises(CategoryPreferencesValidationError, match="duplicate"):
        validate_preferences(prefs)


def test_validate_rejects_duplicate_specific_cell():
    prefs = [
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.HIGH,
            dimension=UsageDimension.STORAGE,
        ),
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.LOW,
            dimension=UsageDimension.STORAGE,
        ),
    ]
    with pytest.raises(CategoryPreferencesValidationError, match="duplicate"):
        validate_preferences(prefs)


def test_validate_allows_same_category_different_dimensions():
    validate_preferences([
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.HIGH,
            dimension=UsageDimension.STORAGE,
        ),
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.MEDIUM,
            dimension=UsageDimension.ACCESS,
        ),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Worked examples from the README
# ─────────────────────────────────────────────────────────────────────────────


def test_readme_example_cosmetic_surgery_app():
    # cosmetic surgery app: biometric and health are both HIGH for everything
    # except surgeon needs biometric ACCESS during consultation.
    prefs = [
        _pref(DataCategory.BIOMETRIC, CategorySensitivity.HIGH),
        _pref(
            DataCategory.BIOMETRIC,
            CategorySensitivity.MEDIUM,
            dimension=UsageDimension.ACCESS,
        ),
        _pref(DataCategory.HEALTH, CategorySensitivity.HIGH),
    ]
    validate_preferences(prefs)

    assert (
        resolve_sensitivity(
            prefs, DataCategory.BIOMETRIC, UsageDimension.THIRD_PARTY_SHARING
        )
        is CategorySensitivity.HIGH
    )
    assert (
        resolve_sensitivity(prefs, DataCategory.BIOMETRIC, UsageDimension.ACCESS)
        is CategorySensitivity.MEDIUM
    )
    assert (
        resolve_sensitivity(prefs, DataCategory.HEALTH, UsageDimension.TRAINING)
        is CategorySensitivity.HIGH
    )


def test_readme_example_pharmacy():
    # Same principal at a pharmacy: health is LOW for storage (expected),
    # HIGH for third-party sharing.
    prefs = [
        _pref(
            DataCategory.HEALTH,
            CategorySensitivity.LOW,
            dimension=UsageDimension.STORAGE,
        ),
        _pref(
            DataCategory.HEALTH,
            CategorySensitivity.HIGH,
            dimension=UsageDimension.THIRD_PARTY_SHARING,
        ),
    ]
    validate_preferences(prefs)

    assert (
        resolve_sensitivity(prefs, DataCategory.HEALTH, UsageDimension.STORAGE)
        is CategorySensitivity.LOW
    )
    assert (
        resolve_sensitivity(
            prefs, DataCategory.HEALTH, UsageDimension.THIRD_PARTY_SHARING
        )
        is CategorySensitivity.HIGH
    )
    # no opinion on access, falls back to LOW default.
    assert (
        resolve_sensitivity(prefs, DataCategory.HEALTH, UsageDimension.ACCESS)
        is CategorySensitivity.LOW
    )
