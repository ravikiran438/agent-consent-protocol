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

"""Adherence trail validator.

Per Anumati §3.3–§3.4 the adherence trail is a singly-linked list of
AdherenceEvent records anchored to a ConsentRecord. This module checks:

  S3  Every event references a valid ConsentRecord.
  S4  Skill invocations are preceded by a permit on an undisputed claim.
      (Enforced here by checking no permit event exists for a disputed
      claim, which is the contrapositive we can verify from the trail
      alone — see S6.)
  S5  A disputed claim produces deny or escalate, never permit.
  S6  No AdherenceEvent for a disputed claim has decision = permit.
      (Logical dual of S5; both are checked.)

Link integrity: the first event has prev_event_id == None; each
subsequent event's prev_event_id points to the previous event's id.
"""

from __future__ import annotations

from typing import Mapping

from acap.types import AdherenceEvent, ConsentRecord


class TrailValidationError(ValueError):
    """Raised when an adherence trail fails validation."""


def _disputed_claim_ids(record: ConsentRecord) -> set[str]:
    return {p.claim_id for p in record.parsed_claims if p.disputed}


def validate_adherence_trail(
    trail: list[AdherenceEvent],
    consent_records: Mapping[str, ConsentRecord],
) -> None:
    """Validate a trail against the consent records it anchors to.

    ``consent_records`` is a dict keyed by record_id. The trail may span
    multiple ConsentRecords (e.g. after a re-consent) but every event's
    consent_record_id MUST resolve to a record in this map.

    Raises TrailValidationError on the first failure.
    """
    if not trail:
        return  # empty trail is structurally fine — nothing to check

    first = trail[0]
    if first.prev_event_id is not None:
        raise TrailValidationError(
            f"first event {first.event_id} has prev_event_id "
            f"{first.prev_event_id!r}; expected None"
        )

    # Pre-compute disputed claim ids per consent record so we don't
    # rebuild the set for every event in a long trail.
    disputed_cache: dict[str, set[str]] = {}

    for i, evt in enumerate(trail):
        # S3 — event anchors to a known ConsentRecord
        consent = consent_records.get(evt.consent_record_id)
        if consent is None:
            raise TrailValidationError(
                f"event {evt.event_id} references unknown "
                f"consent_record_id {evt.consent_record_id!r}"
            )

        # Link integrity
        if i > 0:
            prev = trail[i - 1]
            if evt.prev_event_id != prev.event_id:
                raise TrailValidationError(
                    f"event at index {i} ({evt.event_id}) has "
                    f"prev_event_id {evt.prev_event_id!r}; expected "
                    f"{prev.event_id!r}"
                )

        # S5/S6 — disputed claims can never carry a permit
        if evt.consent_record_id not in disputed_cache:
            disputed_cache[evt.consent_record_id] = _disputed_claim_ids(consent)

        is_disputed = evt.claim_id in disputed_cache[evt.consent_record_id]
        if is_disputed and evt.decision.value == "permit":
            raise TrailValidationError(
                f"event {evt.event_id} permits action on disputed claim "
                f"{evt.claim_id!r} (violates S5/S6)"
            )

        # Sanity check: the event's claim_id should be one the consent
        # record actually parsed. A permit on a claim_id that isn't in
        # the policy is a bug somewhere upstream.
        parsed_ids = {p.claim_id for p in consent.parsed_claims}
        if evt.claim_id not in parsed_ids:
            raise TrailValidationError(
                f"event {evt.event_id} references claim_id "
                f"{evt.claim_id!r} not found in ConsentRecord "
                f"{consent.record_id} (parsed_claims: {sorted(parsed_ids)})"
            )
