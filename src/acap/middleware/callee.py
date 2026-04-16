# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Callee-side ACAP middleware.

Exposes the two HTTP endpoints that the paper's §4.1 describes:

    POST /acap/consent   , accept a ConsentRecord from a caller
    POST /acap/adherence , accept an AdherenceEvent from a caller

and a gating helper ``require_permit()`` that a skill handler can call
before it does any real work. The callee does not mint consent records
or adherence events; it only validates what the caller submits, stores
them for audit, and enforces the invariant that disputed claims can
never produce a permit (§3.2, §3.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, HTTPException

from acap.types import (
    AdherenceEvent,
    ConsentRecord,
    PolicyDocument,
)
from acap.validators import (
    ChainValidationError,
    TrailValidationError,
    validate_adherence_trail,
    validate_consent_record,
)


@dataclass
class ACAPCallee:
    """In-memory ACAP state for a callee agent.

    Stores consent records keyed by caller_agent_id and the adherence
    trail per consent record. Fine for the demo; a production callee
    would persist these to an append-only store.
    """

    policy: PolicyDocument
    consent_by_caller: dict[str, ConsentRecord] = field(default_factory=dict)
    trail_by_consent: dict[str, list[AdherenceEvent]] = field(default_factory=dict)

    # ─── handshake ────────────────────────────────────────────────────

    def accept_consent(self, record: ConsentRecord) -> None:
        """Validate and store a ConsentRecord submitted by a caller."""
        if record.policy_version != self.policy.version:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"ConsentRecord references policy version "
                    f"{record.policy_version!r} but current version is "
                    f"{self.policy.version!r}"
                ),
            )

        try:
            validate_consent_record(record, policy=self.policy)
        except ChainValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        self.consent_by_caller[record.caller_agent_id] = record
        self.trail_by_consent.setdefault(record.record_id, [])

    # ─── per-action adherence ─────────────────────────────────────────

    def accept_adherence(self, event: AdherenceEvent) -> None:
        """Validate and append an AdherenceEvent to the trail."""
        consent = self._find_consent_by_record_id(event.consent_record_id)
        if consent is None:
            raise HTTPException(
                status_code=404,
                detail=f"unknown consent_record_id {event.consent_record_id!r}",
            )

        trail = self.trail_by_consent.setdefault(consent.record_id, [])
        trail.append(event)

        # Re-validate the full trail to catch linked-list breakage.
        try:
            validate_adherence_trail(
                trail, {consent.record_id: consent}
            )
        except TrailValidationError as exc:
            # Roll back the append so the trail stays consistent.
            trail.pop()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ─── gating helper the skill handler calls before work ───────────

    def require_permit(
        self, caller_agent_id: str, claim_id: str
    ) -> AdherenceEvent:
        """Raise 403 unless the latest adherence event for this caller +
        claim is a permit on an undisputed claim.

        Returns the event that authorised the action so the skill
        handler can reference it in its response.
        """
        consent = self.consent_by_caller.get(caller_agent_id)
        if consent is None:
            raise HTTPException(
                status_code=403,
                detail=f"no active ConsentRecord for caller {caller_agent_id!r}",
            )

        trail = self.trail_by_consent.get(consent.record_id, [])
        latest = next(
            (
                e
                for e in reversed(trail)
                if e.claim_id == claim_id
            ),
            None,
        )
        if latest is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"no AdherenceEvent recorded for claim_id {claim_id!r} "
                    f"under ConsentRecord {consent.record_id}"
                ),
            )
        if latest.decision.value != "permit":
            raise HTTPException(
                status_code=403,
                detail=(
                    f"latest AdherenceEvent for claim_id {claim_id!r} is "
                    f"{latest.decision.value!r}, not permit: {latest.reasoning}"
                ),
            )
        return latest

    # ─── audit surface ────────────────────────────────────────────────

    def audit(self, caller_agent_id: str) -> dict:
        """Return a simple chronological audit dump for a given caller."""
        consent = self.consent_by_caller.get(caller_agent_id)
        if consent is None:
            return {"consent": None, "trail": []}
        return {
            "consent": consent.model_dump(mode="json"),
            "trail": [
                e.model_dump(mode="json")
                for e in self.trail_by_consent.get(consent.record_id, [])
            ],
        }

    # ─── internals ────────────────────────────────────────────────────

    def _find_consent_by_record_id(
        self, record_id: str
    ) -> Optional[ConsentRecord]:
        for rec in self.consent_by_caller.values():
            if rec.record_id == record_id:
                return rec
        return None


def build_fastapi_router(callee: ACAPCallee) -> APIRouter:
    """Return a FastAPI router with the two ACAP endpoints mounted."""
    router = APIRouter(prefix="/acap")

    @router.post("/consent")
    async def post_consent(record: ConsentRecord) -> dict:
        callee.accept_consent(record)
        return {"record_id": record.record_id, "status": "accepted"}

    @router.post("/adherence")
    async def post_adherence(event: AdherenceEvent) -> dict:
        callee.accept_adherence(event)
        return {"event_id": event.event_id, "status": "accepted"}

    @router.get("/audit/{caller_agent_id:path}")
    async def get_audit(caller_agent_id: str) -> dict:
        return callee.audit(caller_agent_id)

    return router
