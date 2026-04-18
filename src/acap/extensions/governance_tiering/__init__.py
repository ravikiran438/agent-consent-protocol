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

"""Governance-tiering extension for ACAP.

Adds a supervisory ``governance_agent`` that classifies policy
version bumps into tiered escalations (auto-approved,
governance-reviewed, human-required). The classifier here is a
minimal reference; see ``extensions/governance-tiering/README.md``
for the design and the ``consent.governance.proto`` for the schema.
"""

from acap.extensions.governance_tiering.materiality import (
    MaterialityFactor,
    classify,
    diff_policies,
)
from acap.extensions.governance_tiering.types import (
    ClaimChangeType,
    ClaimDiff,
    DelegationChain,
    DelegationHop,
    EscalationAssessment,
    EscalationTier,
    MaterialitySignal,
    PolicyDiff,
)
from acap.extensions.governance_tiering.validator import (
    GovernanceValidationError,
    validate_delegation_chain,
    validate_escalation_assessment,
)

__all__ = [
    "ClaimChangeType",
    "ClaimDiff",
    "DelegationChain",
    "DelegationHop",
    "EscalationAssessment",
    "EscalationTier",
    "MaterialityFactor",
    "MaterialitySignal",
    "PolicyDiff",
    "classify",
    "diff_policies",
    "GovernanceValidationError",
    "validate_delegation_chain",
    "validate_escalation_assessment",
]

EXTENSION_URI = (
    "https://github.com/ravikiran438/agent-consent-protocol/"
    "extensions/governance-tiering/v1"
)
