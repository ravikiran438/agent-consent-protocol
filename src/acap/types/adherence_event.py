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

"""Adherence event types for the Agent Consent and Adherence Protocol (ACAP).

These types correspond to the AdherenceEvent, AdherenceDecision,
CheckAdherenceRequest, and CheckAdherenceResponse messages in
specification/consent.proto.

AdherenceEvent is the runtime enforcement primitive. Events form a
singly-linked list (via prev_event_id) constituting the proof-of-adherence
trail: a per-action audit record that documents WHICH clause was evaluated,
WHAT decision was reached, and WHY the agent reached it.

This advances beyond human ToS acceptance ("I clicked agree") to a
clause-level reasoning record that agents can produce and humans cannot.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AdherenceDecision(str, Enum):
    """The outcome of evaluating a PolicyClaim at runtime."""

    # The action is permitted under the evaluated claim. Proceed.
    PERMIT = "permit"

    # The action is prohibited under the evaluated claim. Refuse and log.
    DENY = "deny"

    # The claim is ambiguous or in dispute; halt and notify principal.
    ESCALATE = "escalate"


class AdherenceEvent(BaseModel):
    """An append-only record of a single runtime policy enforcement decision.

    Recorded by the calling agent immediately before invoking (or refusing to
    invoke) a callee skill. Events form a singly-linked list via prev_event_id.

    Together with the AgentConsentRecord chain, AdherenceEvents constitute
    "proof of adherence": a reasoning trail that goes beyond mere
    "proof of acceptance" by documenting clause-level justifications.

    Agents SHOULD call RecordAdherence for every skill invocation attempt,
    whether the decision is permit or deny. A deny without a corresponding
    AdherenceEvent cannot be distinguished from a silent failure.
    """

    event_id: str = Field(
        description="UUIDv7 identifier for this event.",
    )
    prev_event_id: Optional[str] = Field(
        default=None,
        description="event_id of the immediately preceding adherence event "
        "for this consent_record_id. Absent for the first event.",
    )
    consent_record_id: str = Field(
        description="record_id of the AgentConsentRecord that authorises the "
        "calling agent to interact with the callee.",
    )
    action: str = Field(
        description="The skill id or action the calling agent attempted "
        "(e.g. 'search_catalog', 'odrl:aggregate').",
    )
    clause_evaluated: str = Field(
        description="clause_ref of the PolicyClaim evaluated to reach this "
        "decision (e.g. '§3.4.2').",
    )
    claim_id: str = Field(
        description="claim_id of the PolicyClaim evaluated.",
    )
    decision: AdherenceDecision = Field(
        description="The enforcement decision for this action.",
    )
    reasoning: str = Field(
        description="The calling agent's natural-language justification for "
        "its decision. This is the 'reasoning' field that makes adherence "
        "auditable and distinguishes ACAP from scope-based auth. "
        "Example: \"Action 'aggregate_sessions' matches prohibition §3.4.2 "
        "(odrl:aggregate on pii:session_data). Denying.\"",
    )
    timestamp: str = Field(
        description="ISO 8601 UTC datetime of this evaluation.",
    )
    context: dict[str, str] = Field(
        default_factory=dict,
        description="Arbitrary key-value context captured at evaluation time "
        "(e.g. task_id, input_mode, originating_skill).",
    )
    agent_signature: Optional[str] = Field(
        default=None,
        description="JWS (compact serialisation) over the canonical JSON of "
        "this event, signed by the calling agent's key. RECOMMENDED.",
    )


class CheckAdherenceRequest(BaseModel):
    """Pre-flight check: evaluate whether an action is permitted under policy.

    Does not record an AdherenceEvent. Use RecordAdherence after the action
    is confirmed to build the auditable trail.
    """

    consent_record_id: str = Field(
        description="record_id of the active AgentConsentRecord for this "
        "caller-callee pair.",
    )
    action: str = Field(
        description="The action to evaluate (skill id or ODRL action term).",
    )
    asset: str = Field(
        description="The asset the action would operate on.",
    )
    context: dict[str, str] = Field(
        default_factory=dict,
        description="Additional context for constraint evaluation "
        "(e.g. {'purpose': 'analytics'}).",
    )


class CheckAdherenceResponse(BaseModel):
    """Result of a pre-flight adherence check."""

    decision: AdherenceDecision = Field(
        description="The enforcement decision.",
    )
    governing_claim_id: str = Field(
        description="claim_id of the PolicyClaim that determined the decision.",
    )
    governing_clause_ref: str = Field(
        description="clause_ref of the governing claim for human-readable "
        "citation (e.g. '§3.4.2').",
    )
    reasoning: str = Field(
        description="Natural-language explanation of the decision.",
    )
