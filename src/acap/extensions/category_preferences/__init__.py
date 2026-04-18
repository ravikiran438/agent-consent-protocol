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

"""Category-preferences extension for ACAP.

Lets a human principal express asymmetric sensitivity across a
(category, dimension) grid that travels with the ``ConsentRecord``.
See ``extensions/category-preferences/README.md`` for the design and
``motivation.md`` for the rationale.
"""

from acap.extensions.category_preferences.resolver import resolve_sensitivity
from acap.extensions.category_preferences.types import (
    CategoryPreference,
    CategorySensitivity,
    DataCategory,
    UsageDimension,
)
from acap.extensions.category_preferences.validator import (
    CategoryPreferencesValidationError,
    validate_preferences,
)

__all__ = [
    "CategoryPreference",
    "CategorySensitivity",
    "DataCategory",
    "UsageDimension",
    "resolve_sensitivity",
    "CategoryPreferencesValidationError",
    "validate_preferences",
]

EXTENSION_URI = (
    "https://github.com/ravikiran438/agent-consent-protocol/"
    "extensions/category-preferences/v1"
)
