# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Strictest-floor computation for the regulatory-context extension.

Combines three inputs to produce the effective sensitivity for one
(category, dimension) query: the principal's preference matrix, the
callee's declared regulatory contexts, and the caller's declared
regulatory contexts. The function is a pure ``max`` over the ordered
sensitivity lattice LOW < MEDIUM < HIGH, so two conformant
implementations will always agree on the floor for a given input.
"""

from __future__ import annotations

from acap.extensions.category_preferences.resolver import resolve_sensitivity
from acap.extensions.category_preferences.types import (
    CategoryPreference,
    CategorySensitivity,
    DataCategory,
    UsageDimension,
)
from acap.extensions.regulatory_context.types import RegulatoryContext


_RANK = {
    CategorySensitivity.LOW: 0,
    CategorySensitivity.MEDIUM: 1,
    CategorySensitivity.HIGH: 2,
}


def max_sensitivity(
    a: CategorySensitivity, b: CategorySensitivity
) -> CategorySensitivity:
    """Return the stricter of two sensitivities."""
    return a if _RANK[a] >= _RANK[b] else b


def compute_floor(
    principal_preferences: list[CategoryPreference],
    contexts: list[RegulatoryContext],
    category: DataCategory,
    dimension: UsageDimension,
) -> CategorySensitivity:
    """Return the strictest applicable sensitivity for a (category, dimension)."""
    floor = resolve_sensitivity(principal_preferences, category, dimension)
    for ctx in contexts:
        for obligation in ctx.obligations:
            if (
                category in obligation.affected_categories
                and dimension in obligation.affected_dimensions
            ):
                floor = max_sensitivity(floor, obligation.minimum_sensitivity)
    return floor
