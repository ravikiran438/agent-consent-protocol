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

"""Consent record types for the Agent Consent and Adherence Protocol (ACAP).

These types correspond to the AgentConsentRecord, ParsedClaim, and
ConsentDecision messages in specification/consent.proto.

The AgentConsentRecord is the foundational audit primitive of ACAP. Records
form a singly-linked list (via prev_record_id) constituting the legally
defensible consent chain for a caller-callee agent pair.

Design note: the linked-list structure is derived from the original human-auth
system in which the same pattern was used to preserve all versions of terms
accepted per user for legal auditability. In A2A context the chain additionally
records the calling agent's parsed understanding of each PolicyClaim, enabling
"proof of adherence" rather than mere "proof of acceptance".
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConsentDecision(str, Enum):
    """The calling agent's overall verdict on a PolicyDocument version."""

    # All claims understood and accepted. Caller may invoke skills.
    ACCEPTED = "accepted"

    # Caller rejects the policy. No skills will be invoked.
    REJECTED = "rejected"

    # Caller accepts with noted disputes; human principal has been notified.
    # Skills may be invoked only for claims not under dispute.
    CONDITIONAL = "conditional"


class ParsedClaim(BaseModel):
    """The calling agent's understanding of a single PolicyClaim.

    Every PolicyClaim in a PolicyDocument MUST have a corresponding ParsedClaim
    in the AgentConsentRecord. This requirement ensures agents cannot silently
    ignore inconvenient clauses.
    """

    claim_id: str = Field(
        description="claim_id from the PolicyClaim this entry covers.",
    )
    understood: bool = Field(
        description="Whether the calling agent understood the claim well enough "
        "to act on it. False SHOULD trigger escalation to the human principal.",
    )
    disputed: bool = Field(
        description="Whether the calling agent disputes the claim "
        "(e.g. ambiguous scope, conflict with another policy).",
    )
    dispute_reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of the dispute. "
        "REQUIRED when disputed is true.",
    )


class AgentConsentRecord(BaseModel):
    """An append-only entry in the per-agent-pair consent chain.

    Documents the calling agent's parsed understanding of and decision about
    a specific PolicyDocument version. Records form a singly-linked list via
    prev_record_id.

    A new record MUST be created whenever:
      (a) the callee agent publishes a new PolicyDocument version, or
      (b) the calling agent's principal identity changes.

    Legal note: under UETA §14, the human principal identified by
    principal_id is bound by this record. The chain is the mechanism by which
    agents protect their principals from unknown ToS liability: each record
    proves the agent parsed and reasoned about the terms before acting.

    Records SHOULD be stored by both parties and submitted to a neutral
    audit endpoint (acceptance_endpoint on the UsagePolicyRef).
    """

    record_id: str = Field(
        description="UUIDv7 identifier for this record.",
    )
    prev_record_id: Optional[str] = Field(
        default=None,
        description="record_id of the immediately preceding record in the "
        "consent chain for this caller-callee pair. Absent only for the "
        "first record.",
    )
    caller_agent_id: str = Field(
        description="DID or HTTPS URL identifying the calling agent.",
    )
    callee_agent_id: str = Field(
        description="DID or HTTPS URL identifying the callee agent.",
    )
    policy_version: str = Field(
        description="Semver of the PolicyDocument this record covers.",
    )
    policy_hash: str = Field(
        description="SHA-256 hex digest of the PolicyDocument at time of "
        "acceptance. Provides tamper evidence independent of URI availability. "
        "Format: 'sha256:<hex>'.",
    )
    parsed_claims: list[ParsedClaim] = Field(
        description="The caller's parsed interpretation of each PolicyClaim. "
        "MUST include an entry for every claim in the PolicyDocument.",
    )
    decision: ConsentDecision = Field(
        description="The caller's overall decision.",
    )
    accepted_at: str = Field(
        description="ISO 8601 UTC datetime of this decision.",
    )
    valid_until: str = Field(
        description="ISO 8601 UTC datetime or the sentinel value "
        "'on_version_bump' indicating when this record expires. "
        "'on_version_bump' means the record is invalidated when the callee "
        "publishes a new PolicyDocument version.",
    )
    caller_signature: Optional[str] = Field(
        default=None,
        description="JWS (JSON Web Signature, compact serialisation) over the "
        "canonical JSON of this record, signed by the calling agent's key. "
        "RECOMMENDED for non-repudiation.",
    )
    principal_id: Optional[str] = Field(
        default=None,
        description="Identifier of the human principal on whose behalf the "
        "calling agent is acting. When present, establishes the "
        "human-in-the-loop accountability chain required by UETA §14.",
    )
