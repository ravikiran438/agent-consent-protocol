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

"""Matrix resolver for the category-preferences extension.

Given a list of ``CategoryPreference`` entries and a (category,
dimension) query, return the applicable ``CategorySensitivity``. The
resolution rule is simple:

    1. A preference with a matching ``(category, dimension)`` pair wins.
    2. Otherwise, a preference with matching category and no dimension
       (the default row) wins.
    3. Otherwise, ``CategorySensitivity.LOW`` is returned, on the
       principle that absence of an opinion is not a high-sensitivity
       claim.

Callers that want a stricter default should filter the list before
calling, or compose the result with a regulatory-context floor via the
regulatory-context extension.
"""

from __future__ import annotations

from acap.extensions.category_preferences.types import (
    CategoryPreference,
    CategorySensitivity,
    DataCategory,
    UsageDimension,
)


def resolve_sensitivity(
    preferences: list[CategoryPreference],
    category: DataCategory,
    dimension: UsageDimension,
) -> CategorySensitivity:
    """Return the applicable sensitivity for a (category, dimension) query."""
    default: CategorySensitivity | None = None
    for p in preferences:
        if p.category != category:
            continue
        if p.dimension == dimension:
            return p.sensitivity
        if p.dimension is None:
            default = p.sensitivity
    return default or CategorySensitivity.LOW
