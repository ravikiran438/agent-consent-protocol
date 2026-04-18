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

"""Audit-projection extension for ACAP.

Projects the machine-readable consent chain and adherence trail into
structured, plain-English audit artefacts suitable for compliance
officers, legal teams, and regulators. The projection is lossless:
every narrative entry carries a back-reference to the signed
``ConsentRecord`` or ``AdherenceEvent`` it summarizes. See
``extensions/audit-projection/motivation.md`` for the rationale.
"""

from acap.extensions.audit_projection.projector import generate_report
from acap.extensions.audit_projection.types import (
    AuditEntry,
    AuditEntryType,
    AuditReport,
    AuditReportRequest,
    ClaimAuditSummary,
    VersionAuditSummary,
)
from acap.extensions.audit_projection.validator import (
    AuditReportValidationError,
    validate_audit_report,
)

__all__ = [
    "AuditEntry",
    "AuditEntryType",
    "AuditReport",
    "AuditReportRequest",
    "ClaimAuditSummary",
    "VersionAuditSummary",
    "generate_report",
    "AuditReportValidationError",
    "validate_audit_report",
]

EXTENSION_URI = (
    "https://github.com/ravikiran438/agent-consent-protocol/"
    "extensions/audit-projection/v1"
)
