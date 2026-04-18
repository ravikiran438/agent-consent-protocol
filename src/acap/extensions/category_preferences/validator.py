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

"""Validator for the category-preferences extension.

Rejects a preference list with ambiguous cells: a `(category, dimension)`
pair must appear at most once, otherwise the resolver's result is
order-dependent.
"""

from __future__ import annotations

from acap.extensions.category_preferences.types import CategoryPreference


class CategoryPreferencesValidationError(ValueError):
    """Raised when a preference list violates the uniqueness invariant."""


def validate_preferences(preferences: list[CategoryPreference]) -> None:
    """Ensure no two preferences share the same (category, dimension) cell."""
    seen: dict[tuple, int] = {}
    for i, p in enumerate(preferences):
        key = (p.category, p.dimension)
        if key in seen:
            raise CategoryPreferencesValidationError(
                f"duplicate preference for category {p.category.value!r} "
                f"dimension {p.dimension.value if p.dimension else 'default'!r} "
                f"at index {i} (first at index {seen[key]})"
            )
        seen[key] = i
