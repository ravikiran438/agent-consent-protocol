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

"""Runtime validators for ACAP consent chains and adherence trails.

These are reference implementations of the integrity checks described
in the Anumati paper §3.2–§3.4. They are intentionally small — the
goal is a correct, readable artifact that other implementers can port,
not a fully-featured library.
"""

from acap.validators.chain import (
    ChainValidationError,
    validate_consent_chain,
    validate_consent_record,
)
from acap.validators.hash import (
    canonicalize,
    compute_policy_hash,
    verify_policy_hash,
)
from acap.validators.trail import (
    TrailValidationError,
    validate_adherence_trail,
)

__all__ = [
    "ChainValidationError",
    "TrailValidationError",
    "canonicalize",
    "compute_policy_hash",
    "validate_adherence_trail",
    "validate_consent_chain",
    "validate_consent_record",
    "verify_policy_hash",
]
