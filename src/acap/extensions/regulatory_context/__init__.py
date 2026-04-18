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

"""Regulatory-context extension for ACAP.

Carries jurisdictional regulatory obligations through the consent
chain as a floor that neither the callee's policy nor the principal's
preferences can lower. This extension provides the envelope; specific
regulatory mappings (HIPAA, GDPR, PCI-DSS, EU AI Act, and others) are
NOT part of the reference implementation and require qualified legal
review before they ship as reference material. See
``extensions/regulatory-context/motivation.md`` for the rationale.
"""

from acap.extensions.regulatory_context.floor import (
    compute_floor,
    max_sensitivity,
)
from acap.extensions.regulatory_context.types import (
    ComplianceObligation,
    RegulatoryContext,
    RegulatoryFramework,
)
from acap.extensions.regulatory_context.validator import (
    RegulatoryContextValidationError,
    validate_regulatory_context,
)

__all__ = [
    "ComplianceObligation",
    "RegulatoryContext",
    "RegulatoryFramework",
    "compute_floor",
    "max_sensitivity",
    "RegulatoryContextValidationError",
    "validate_regulatory_context",
]

EXTENSION_URI = (
    "https://github.com/ravikiran438/agent-consent-protocol/"
    "extensions/regulatory-context/v1"
)
