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

"""Policy document types for the Agent Consent and Adherence Protocol (ACAP).

These types correspond to the PolicyDocument, PolicyClaim, RuleType, and
UsagePolicyRef messages in specification/consent.proto.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RuleType(str, Enum):
    """Whether a PolicyClaim permits, prohibits, or obligates an action.

    Mirrors the ODRL 2.2 Rule vocabulary (https://www.w3.org/TR/odrl-vocab/).
    """

    PERMISSION = "permission"
    PROHIBITION = "prohibition"
    OBLIGATION = "obligation"


class PolicyClaim(BaseModel):
    """A single machine-readable rule derived from a natural-language clause.

    Vocabulary aligns with ODRL 2.2 (W3C). Agents parse claims to build a
    structured understanding of what they may, may not, or must do when
    calling a callee agent's skills.

    Example:
        {
          "claim_id": "3f7a1b2c-...",
          "clause_ref": "§3.4.2",
          "action": "odrl:aggregate",
          "asset": "pii:session_data",
          "rule_type": "prohibition",
          "constraint": "odrl:purpose isNot behavioral_profiling",
          "effective_version": "2.1.0"
        }
    """

    claim_id: str = Field(
        description="Stable identifier for this claim within the document. "
        "UUIDv4 RECOMMENDED.",
    )
    clause_ref: str = Field(
        description="Reference to the natural-language clause(s) from which "
        "this claim is derived (e.g. '§3.4.2', 'Section 5(b)').",
    )
    action: str = Field(
        description="The action governed by this rule. SHOULD use ODRL 2.2 "
        "action vocabulary where applicable "
        "(e.g. 'odrl:aggregate', 'a2a:invoke_skill').",
    )
    asset: str = Field(
        description="The asset or asset class to which the rule applies "
        "(e.g. 'pii:session_data', 'a2a:task_output', 'odrl:All').",
    )
    rule_type: RuleType = Field(
        description="Whether this rule permits, prohibits, or obligates "
        "the action on the asset.",
    )
    constraint: Optional[str] = Field(
        default=None,
        description="ODRL constraint expression further scoping when this rule "
        "applies. When absent the rule applies unconditionally.",
    )
    effective_version: str = Field(
        description="The policy semver in which this claim was first introduced.",
    )
    escalate_on_deny: Optional[bool] = Field(
        default=None,
        description="If true, agents MUST halt and notify the human principal "
        "on deny rather than silently refusing.",
    )


class PolicyDocument(BaseModel):
    """The versioned, machine-readable usage policy published by a callee agent.

    A PolicyDocument is referenced from an A2A AgentCard via the
    capabilities.extensions mechanism and hosted at a well-known URL
    (e.g. /.well-known/usage-policy.json).

    The content hash provides tamper-evidence independent of URI availability.
    """

    version: str = Field(
        description="Semantic version of this document (semver, e.g. '2.1.0').",
    )
    document_uri: str = Field(
        description="Canonical HTTPS URI where this document is hosted. "
        "Agents MUST verify document_hash before parsing claims.",
    )
    document_hash: str = Field(
        description="SHA-256 hex digest of the canonical JSON serialisation. "
        "Format: 'sha256:<hex>'.",
    )
    effective_date: str = Field(
        description="ISO 8601 UTC datetime from which this version is effective.",
    )
    supersedes: Optional[str] = Field(
        default=None,
        description="Semver of the PolicyDocument this version supersedes. "
        "Absent on the initial version.",
    )
    change_summary: Optional[str] = Field(
        default=None,
        description="Human-readable summary of material changes. Enables "
        "agents to surface change context to their principal.",
    )
    claims: list[PolicyClaim] = Field(
        description="Ordered list of machine-readable policy rules. "
        "At least one claim MUST be present.",
    )
    publisher: str = Field(
        description="DID or HTTPS URL identifying the entity that published "
        "this document.",
    )
    natural_language_uri: str = Field(
        description="HTTPS URL of the human-readable Terms of Service / "
        "Privacy Policy that this document is derived from. "
        "Serves as the legal ground truth.",
    )
    jurisdictions: list[str] = Field(
        default_factory=list,
        description="Jurisdiction(s) under which this policy is governed "
        "(e.g. ['GDPR', 'CCPA']). Informs agents in regulated environments.",
    )


class UsagePolicyRef(BaseModel):
    """Pointer to a callee agent's PolicyDocument, embedded in the A2A AgentCard.

    Added as a top-level 'usage_policy' field in the AgentCard JSON when the
    ACAP extension URI is declared in capabilities.extensions:

        {
          "capabilities": {
            "extensions": [
              {
                "uri": "https://a2aproject.github.io/consent/v1",
                "description": "Supports the Agent Consent and Adherence Protocol.",
                "required": true
              }
            ]
          },
          "usage_policy": { ... }
        }

    Callers MUST fetch and verify the full PolicyDocument from document_uri
    before invoking any skill when acceptance_required is true.
    """

    version: str = Field(
        description="Semver of the current PolicyDocument.",
    )
    document_uri: str = Field(
        description="HTTPS URL where the PolicyDocument JSON is hosted.",
    )
    document_hash: str = Field(
        description="SHA-256 hex digest of the current PolicyDocument. "
        "Format: 'sha256:<hex>'.",
    )
    effective_date: str = Field(
        description="ISO 8601 UTC datetime from which this version is effective.",
    )
    acceptance_required: bool = Field(
        description="Whether callers MUST complete the ACAP consent handshake "
        "before invoking any skill.",
    )
    acceptance_endpoint: Optional[str] = Field(
        default=None,
        description="HTTPS endpoint at which callers POST a ConsentRecord. "
        "REQUIRED when acceptance_required is true.",
    )
    supersedes: Optional[str] = Field(
        default=None,
        description="Semver of the previous PolicyDocument version.",
    )
    change_summary: Optional[str] = Field(
        default=None,
        description="One-line summary of material changes for agent reasoning.",
    )
    natural_language_uri: str = Field(
        description="HTTPS URL of the human-readable Terms of Service.",
    )
