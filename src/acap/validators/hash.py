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

"""Canonical JSON + SHA-256 for PolicyDocument content-addressing.

Implements the hashing convention from Anumati §3.1: the `hash` field
in PolicyDocument is the SHA-256 of the canonical JSON serialisation
of the document itself, with the `hash` field set to the empty string
before hashing. This breaks the circularity problem, the digest input
never contains the digest.

Canonicalisation follows RFC 8785 (JSON Canonicalization Scheme):
  - UTF-8 encoding
  - Object keys sorted lexicographically
  - No insignificant whitespace
  - Numbers in shortest round-trip form

We don't use a full RFC 8785 library here because the inputs are
JSON-safe (no raw floats, no special Unicode tricks). If you need
full JCS compliance for non-ACAP use, reach for an actual JCS lib.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from acap.types import PolicyDocument

HASH_PREFIX = "sha256:"


def canonicalize(obj: Any) -> bytes:
    """Canonical JSON per RFC 8785 (subset we need).

    Raises TypeError if the input contains types json.dumps can't handle.
    Deliberately strict: NaN/Infinity are rejected.
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _policy_dict_for_hashing(doc: PolicyDocument) -> dict:
    """Serialize a PolicyDocument and zero out the hash field.

    Pydantic's model_dump gives us a plain dict we can mutate before
    hashing. Using `mode="json"` so enums etc. serialise the same way
    they would over the wire.
    """
    d = doc.model_dump(mode="json", exclude_none=True)
    d["document_hash"] = ""
    return d


def compute_policy_hash(doc: PolicyDocument) -> str:
    """Return the canonical SHA-256 hash for a PolicyDocument.

    The returned string includes the ``sha256:`` prefix so it can be
    stored directly in the ``document_hash`` field.
    """
    payload = canonicalize(_policy_dict_for_hashing(doc))
    digest = hashlib.sha256(payload).hexdigest()
    return f"{HASH_PREFIX}{digest}"


def verify_policy_hash(doc: PolicyDocument, expected: str) -> bool:
    """True if ``expected`` matches the hash computed from ``doc``.

    Handles both the prefixed form (``sha256:<hex>``) and bare hex, since
    early adopters sometimes forget the prefix.
    """
    if not expected:
        return False

    expected_norm = expected
    if not expected_norm.startswith(HASH_PREFIX):
        # tolerate bare hex, but the canonical form always has the prefix
        expected_norm = f"{HASH_PREFIX}{expected_norm}"

    return compute_policy_hash(doc) == expected_norm
