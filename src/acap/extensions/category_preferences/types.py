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

"""Types for the category-preferences extension.

Mirrors the messages in ``extensions/category-preferences/consent.categories.proto``.
The vocabularies are intentionally coarse, nine categories and eight
dimensions, so that a human principal can reason about a cell without
understanding the ODRL action/asset vocabulary underneath.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DataCategory(str, Enum):
    """Kind of data the principal cares about."""

    BIOMETRIC = "biometric"
    HEALTH = "health"
    FINANCIAL = "financial"
    LOCATION = "location"
    BEHAVIORAL = "behavioral"
    IDENTITY = "identity"
    COMMUNICATIONS = "communications"
    MINOR_OR_DEPENDENT = "minor_or_dependent"
    OPERATIONAL = "operational"


class UsageDimension(str, Enum):
    """Kind of operation the callee wants to perform on the data."""

    STORAGE = "storage"
    ACCESS = "access"
    THIRD_PARTY_SHARING = "third_party_sharing"
    AUTOMATED_DECISION = "automated_decision"
    TRAINING = "training"
    AGGREGATION = "aggregation"
    CROSS_CONTEXT_USE = "cross_context_use"
    DELETION_OR_PORTABILITY = "deletion_or_portability"


class CategorySensitivity(str, Enum):
    """The principal's sensitivity for a (category, dimension) cell.

    Ordered LOW < MEDIUM < HIGH. ``resolve_sensitivity`` returns the
    strictest of the applicable cells.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CategoryPreference(BaseModel):
    """One cell in the (category, dimension) sensitivity matrix.

    A preference with ``dimension`` left as ``None`` acts as the default
    row for that category; a preference with a specific ``dimension``
    overrides the default for that one cell. A preference with
    ``category`` as ``None`` is ignored (no useful interpretation).
    """

    category: DataCategory = Field(
        description="The data category this preference applies to.",
    )
    sensitivity: CategorySensitivity = Field(
        description="The principal's sensitivity for this "
        "(category, dimension) pair.",
    )
    dimension: Optional[UsageDimension] = Field(
        default=None,
        description="The usage dimension this preference applies to. "
        "When absent, the sensitivity applies as the default for ALL "
        "dimensions of this category. A specific dimension entry "
        "overrides the default.",
    )
    note: Optional[str] = Field(
        default=None,
        description="Optional natural-language note from the principal "
        "(e.g. 'I have dependants, do not share any minor data').",
    )
