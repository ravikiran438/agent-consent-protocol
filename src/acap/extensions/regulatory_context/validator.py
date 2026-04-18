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

"""Structural validator for the regulatory-context extension.

This validator enforces structural well-formedness only. It deliberately
makes NO claims about whether a declared ``RegulatoryContext``
accurately represents the cited regulation; that is a legal
determination and requires qualified review.
"""

from __future__ import annotations

from acap.extensions.regulatory_context.types import RegulatoryContext


class RegulatoryContextValidationError(ValueError):
    """Raised when a RegulatoryContext violates structural invariants."""


def validate_regulatory_context(ctx: RegulatoryContext) -> None:
    """Enforce structural well-formedness on a RegulatoryContext.

    Rejects:
      (a) Empty or whitespace-only ``role``.
      (b) Duplicate ``obligation_ref`` within the same context.
      (c) Empty or whitespace-only ``obligation_ref`` on any obligation.
    """
    if not ctx.role.strip():
        raise RegulatoryContextValidationError(
            f"framework {ctx.framework.value!r} declares an empty role"
        )

    seen: dict[str, int] = {}
    for i, obligation in enumerate(ctx.obligations):
        ref = obligation.obligation_ref.strip()
        if not ref:
            raise RegulatoryContextValidationError(
                f"obligation at index {i} has an empty obligation_ref"
            )
        if ref in seen:
            raise RegulatoryContextValidationError(
                f"duplicate obligation_ref {ref!r} at index {i} "
                f"(first at index {seen[ref]})"
            )
        seen[ref] = i
