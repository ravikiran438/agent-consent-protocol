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

"""Types for the regulatory-context extension.

Mirrors the messages in ``extensions/regulatory-context/consent.regulatory.proto``.
Reuses the ``DataCategory``, ``UsageDimension``, and
``CategorySensitivity`` vocabularies from the category-preferences
extension so that regulatory obligations, callee declarations, and
principal preferences all compose on the same two-axis grid.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from acap.extensions.category_preferences.types import (
    CategorySensitivity,
    DataCategory,
    UsageDimension,
)


class RegulatoryFramework(str, Enum):
    """Jurisdictional regime under which a party declares a context."""

    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    CCPA = "ccpa"
    EU_AI_ACT = "eu_ai_act"
    COPPA = "coppa"
    SOC2 = "soc2"
    FINRA = "finra"


class ComplianceObligation(BaseModel):
    """A single framework requirement expressed on the ACAP grid.

    The obligation is the behavioral constraint, not the legal text.
    ``obligation_ref`` points back to the source article; ``description``
    is the audit-facing summary. The mapping from article to
    ``(affected_categories, affected_dimensions, minimum_sensitivity)``
    is a legal determination and is NOT authored by this extension.
    """

    obligation_ref: str = Field(
        description="Stable human-readable identifier for the source "
        "obligation (e.g. 'HIPAA-164.502(a)').",
    )
    affected_categories: list[DataCategory] = Field(
        description="Data categories this obligation applies to. At "
        "least one entry.",
        min_length=1,
    )
    affected_dimensions: list[UsageDimension] = Field(
        description="Usage dimensions this obligation constrains. At "
        "least one entry.",
        min_length=1,
    )
    minimum_sensitivity: CategorySensitivity = Field(
        description="The floor this obligation enforces on every "
        "(category, dimension) pair in its cross product.",
    )
    description: str = Field(
        description="Natural-language summary of the obligation, for "
        "audit-report consumers.",
    )


class RegulatoryContext(BaseModel):
    """A party's declared regulatory posture.

    Published by callees on the ``PolicyDocument`` envelope and by
    callers on the ``ConsentRecord`` envelope. When two parties declare
    different frameworks, the compliance agent applies the union of
    obligations; when the same framework is declared twice, the
    stricter minimum_sensitivity wins per (category, dimension) cell.
    """

    framework: RegulatoryFramework = Field(
        description="The regulatory framework this context declares.",
    )
    role: str = Field(
        description="The declaring party's role under the framework "
        "(e.g. 'data_controller', 'covered_entity', 'merchant'). "
        "Left as a free-form string until a vocabulary working group "
        "stabilizes a closed set.",
    )
    obligations: list[ComplianceObligation] = Field(
        description="Specific obligations this context carries. At "
        "least one entry.",
        min_length=1,
    )
    jurisdictions: list[str] = Field(
        default_factory=list,
        description="ISO 3166-1 alpha-2 codes (or composite codes like "
        "'US-CA') identifying where the framework applies.",
    )
    always_notify_principal: bool = Field(
        default=False,
        description="Whether the framework requires notification at "
        "ALL escalation tiers, not just HUMAN_REQUIRED. True for EU "
        "AI Act Art. 50 and some GDPR interpretations.",
    )
