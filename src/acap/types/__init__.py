# Copyright 2026 the ACAP Authors
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

"""Agent Consent and Adherence Protocol (ACAP) type definitions.

These types are derived from the normative proto3 definition in
specification/consent.proto and follow the same structure and naming
conventions as the Agent Payments Protocol (AP2) type library.
"""

from acap.types.adherence_event import (
    AdherenceDecision,
    AdherenceEvent,
    CheckAdherenceRequest,
    CheckAdherenceResponse,
)
from acap.types.consent_record import (
    ConsentRecord,
    ConsentDecision,
    ParsedClaim,
)
from acap.types.policy_document import (
    PolicyClaim,
    PolicyDocument,
    RuleType,
    UsagePolicyRef,
)

__all__ = [
    # Policy document
    "PolicyDocument",
    "PolicyClaim",
    "RuleType",
    "UsagePolicyRef",
    # Consent record
    "ConsentRecord",
    "ParsedClaim",
    "ConsentDecision",
    # Adherence event
    "AdherenceEvent",
    "AdherenceDecision",
    "CheckAdherenceRequest",
    "CheckAdherenceResponse",
]
