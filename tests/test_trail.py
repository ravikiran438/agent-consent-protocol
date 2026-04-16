# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""Tests for acap.validators.trail."""

from __future__ import annotations

import pytest

from acap.types import AdherenceDecision
from acap.validators.trail import TrailValidationError, validate_adherence_trail
from tests.conftest import make_event


def test_empty_trail_is_ok(first_record):
    validate_adherence_trail([], {first_record.record_id: first_record})


def test_single_permit_ok(first_record):
    evt = make_event(
        "evt-1",
        prev=None,
        consent_record_id=first_record.record_id,
        claim_id="claim-a",
        decision=AdherenceDecision.PERMIT,
    )
    validate_adherence_trail([evt], {first_record.record_id: first_record})


def test_first_event_cannot_have_prev(first_record):
    evt = make_event(
        "evt-1",
        prev="evt-0",
        consent_record_id=first_record.record_id,
        claim_id="claim-a",
        decision=AdherenceDecision.PERMIT,
    )
    with pytest.raises(TrailValidationError, match="prev_event_id"):
        validate_adherence_trail([evt], {first_record.record_id: first_record})


def test_unknown_consent_record_rejected(first_record):
    evt = make_event(
        "evt-1",
        prev=None,
        consent_record_id="rec-nonexistent",
        claim_id="claim-a",
        decision=AdherenceDecision.PERMIT,
    )
    with pytest.raises(TrailValidationError, match="unknown"):
        validate_adherence_trail([evt], {first_record.record_id: first_record})


def test_permit_on_disputed_claim_rejected(conditional_record):
    """S5/S6: a disputed claim can never carry a permit."""
    evt = make_event(
        "evt-1",
        prev=None,
        consent_record_id=conditional_record.record_id,
        claim_id="claim-b",  # this is the disputed one in the fixture
        decision=AdherenceDecision.PERMIT,
    )
    with pytest.raises(TrailValidationError, match="disputed"):
        validate_adherence_trail(
            [evt], {conditional_record.record_id: conditional_record}
        )


def test_deny_on_disputed_claim_ok(conditional_record):
    """Deny is exactly what S5 expects for disputed claims."""
    evt = make_event(
        "evt-1",
        prev=None,
        consent_record_id=conditional_record.record_id,
        claim_id="claim-b",
        decision=AdherenceDecision.DENY,
    )
    validate_adherence_trail(
        [evt], {conditional_record.record_id: conditional_record}
    )


def test_escalate_on_disputed_claim_ok(conditional_record):
    evt = make_event(
        "evt-1",
        prev=None,
        consent_record_id=conditional_record.record_id,
        claim_id="claim-b",
        decision=AdherenceDecision.ESCALATE,
    )
    validate_adherence_trail(
        [evt], {conditional_record.record_id: conditional_record}
    )


def test_unknown_claim_id_rejected(first_record):
    """An event referencing a claim_id not in the ConsentRecord is a bug."""
    evt = make_event(
        "evt-1",
        prev=None,
        consent_record_id=first_record.record_id,
        claim_id="claim-not-in-policy",
        decision=AdherenceDecision.PERMIT,
    )
    with pytest.raises(TrailValidationError, match="not found"):
        validate_adherence_trail([evt], {first_record.record_id: first_record})


def test_trail_link_integrity(first_record):
    a = make_event(
        "evt-1",
        prev=None,
        consent_record_id=first_record.record_id,
        claim_id="claim-a",
        decision=AdherenceDecision.PERMIT,
    )
    b = make_event(
        "evt-2",
        prev="evt-1",
        consent_record_id=first_record.record_id,
        claim_id="claim-b",
        decision=AdherenceDecision.PERMIT,
    )
    validate_adherence_trail([a, b], {first_record.record_id: first_record})


def test_trail_broken_link_rejected(first_record):
    a = make_event(
        "evt-1",
        prev=None,
        consent_record_id=first_record.record_id,
        claim_id="claim-a",
        decision=AdherenceDecision.PERMIT,
    )
    b = make_event(
        "evt-2",
        prev="evt-wrong",
        consent_record_id=first_record.record_id,
        claim_id="claim-b",
        decision=AdherenceDecision.PERMIT,
    )
    with pytest.raises(TrailValidationError, match="prev_event_id"):
        validate_adherence_trail([a, b], {first_record.record_id: first_record})


def test_trail_spanning_two_consent_records(first_record, conditional_record):
    """Trail can cross a re-consent boundary; events just need to
    resolve to *some* record in the map."""
    a = make_event(
        "evt-1",
        prev=None,
        consent_record_id=first_record.record_id,
        claim_id="claim-a",
        decision=AdherenceDecision.PERMIT,
    )
    b = make_event(
        "evt-2",
        prev="evt-1",
        consent_record_id=conditional_record.record_id,
        claim_id="claim-c",
        decision=AdherenceDecision.PERMIT,
    )
    records = {
        first_record.record_id: first_record,
        conditional_record.record_id: conditional_record,
    }
    validate_adherence_trail([a, b], records)
