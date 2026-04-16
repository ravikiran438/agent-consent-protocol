# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Caller-side ACAP middleware.

Wraps a calling agent's outbound interactions with the consent
handshake and per-action adherence recording described in §4.1 of the
Anumati paper. The middleware is intentionally framework-agnostic;
it does not assume a specific agent SDK. Demos in `demo/` show how it
composes with Google ADK and a plain FastAPI callee.

Typical usage:

    caller = ACAPCaller(
        caller_agent_id="did:agent:marketing-insights",
        principal_id="principal:ravi@example.com",
        claim_parser=GeminiClaimParser(model="gemini-2.5-flash"),
    )

    # Before invoking any skill on a new callee:
    await caller.bind(callee_base_url="https://callee.example.com")

    # Per-action, before the skill HTTP call:
    decision = await caller.check_and_record(
        callee_base_url="https://callee.example.com",
        action="odrl:aggregate",
        claim_id="claim-aggregation-prohibition",
        clause_evaluated="§3.4",
        context={"purpose": "statistical_analysis"},
    )
    if decision.decision.value != "permit":
        raise PermissionError(decision.reasoning)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Protocol

import httpx

from acap.types import (
    AdherenceDecision,
    AdherenceEvent,
    ConsentDecision,
    ConsentRecord,
    ParsedClaim,
    PolicyClaim,
    PolicyDocument,
    RuleType,
)
from acap.validators.hash import compute_policy_hash


# ───────────────────────────────────────────────────────────────────────
# Claim parser protocol, swappable backends
# ───────────────────────────────────────────────────────────────────────


class ClaimParser(Protocol):
    """Pluggable policy-claim interpreter.

    Implementations decide whether a claim is understood and whether it
    is disputed. Deterministic parsers (rule-based, keyword) are fine.
    An LLM-backed parser is provided via :class:`GeminiClaimParser`.
    """

    def parse(self, claim: PolicyClaim, caller_intent: str) -> ParsedClaim:
        """Return a ParsedClaim for the given PolicyClaim.

        ``caller_intent`` is a short free-text description of what the
        caller plans to do with the callee's skills. It is used by
        LLM-backed parsers to detect whether any claim conflicts with
        that intent.
        """
        ...


# ───────────────────────────────────────────────────────────────────────
# Policy cache + the caller itself
# ───────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


@dataclass
class _CalleeBinding:
    """State the caller holds for a single callee it has bound to."""

    policy: PolicyDocument
    consent_record: ConsentRecord
    last_event_id: Optional[str] = None


@dataclass
class ACAPCaller:
    """The caller-side middleware object.

    One instance is usually shared across a calling agent's interactions
    with many callees. Internally it keeps one :class:`_CalleeBinding`
    per callee it has completed a consent handshake with.
    """

    caller_agent_id: str
    claim_parser: ClaimParser
    principal_id: Optional[str] = None
    caller_intent: str = "general analytics over customer-provided data"
    http: httpx.AsyncClient = field(default_factory=httpx.AsyncClient)
    bindings: dict[str, _CalleeBinding] = field(default_factory=dict)

    # ─── handshake ────────────────────────────────────────────────────

    async def bind(
        self,
        callee_base_url: str,
    ) -> ConsentRecord:
        """Fetch the callee's PolicyDocument, parse claims, POST consent.

        Returns the ConsentRecord that was successfully accepted by the
        callee. Idempotent, calling twice against the same callee with
        the same policy version returns the cached record.
        """
        existing = self.bindings.get(callee_base_url)

        # 1. Fetch the AgentCard and extract the usage_policy extension.
        agent_card_url = f"{callee_base_url.rstrip('/')}/.well-known/agent-card.json"
        resp = await self.http.get(agent_card_url)
        resp.raise_for_status()
        agent_card = resp.json()

        usage_policy = agent_card.get("usage_policy")
        if not usage_policy:
            raise RuntimeError(
                f"callee {callee_base_url} does not advertise an ACAP usage_policy "
                "in its AgentCard; ACAP cannot bind"
            )

        policy_version = usage_policy["version"]
        if existing and existing.policy.version == policy_version:
            return existing.consent_record  # nothing to do

        # 2. Fetch the full PolicyDocument.
        policy_resp = await self.http.get(usage_policy["document_uri"])
        policy_resp.raise_for_status()
        policy = PolicyDocument.model_validate(policy_resp.json())

        # 3. Verify content-addressed hash (§3.1).
        computed_hash = compute_policy_hash(policy)
        advertised_hash = usage_policy["document_hash"]
        if computed_hash != advertised_hash:
            raise RuntimeError(
                f"PolicyDocument hash mismatch for {callee_base_url}: "
                f"advertised {advertised_hash!r}, computed {computed_hash!r}"
            )

        # 4. Parse every claim. This is the paper's "critical invariant"
        #    from §3.2, every PolicyClaim MUST have a ParsedClaim.
        parsed = [
            self.claim_parser.parse(c, self.caller_intent) for c in policy.claims
        ]

        # 5. Decide accepted / conditional / rejected based on the parse.
        if any(not p.understood for p in parsed):
            decision = ConsentDecision.REJECTED
        elif any(p.disputed for p in parsed):
            decision = ConsentDecision.CONDITIONAL
        else:
            decision = ConsentDecision.ACCEPTED

        # 6. Assemble and POST the ConsentRecord.
        record = ConsentRecord(
            record_id=str(uuid.uuid4()),
            prev_record_id=(existing.consent_record.record_id if existing else None),
            caller_agent_id=self.caller_agent_id,
            callee_agent_id=usage_policy.get("publisher") or callee_base_url,
            policy_version=policy.version,
            policy_hash=policy.document_hash,
            parsed_claims=parsed,
            decision=decision,
            accepted_at=_now_iso(),
            valid_until="on_version_bump",
            principal_id=self.principal_id,
        )

        acceptance_endpoint = usage_policy["acceptance_endpoint"]
        post = await self.http.post(
            acceptance_endpoint, json=json.loads(record.model_dump_json())
        )
        post.raise_for_status()

        self.bindings[callee_base_url] = _CalleeBinding(
            policy=policy, consent_record=record
        )
        return record

    # ─── per-action adherence ─────────────────────────────────────────

    async def check_and_record(
        self,
        callee_base_url: str,
        action: str,
        claim_id: str,
        clause_evaluated: str,
        context: Optional[dict[str, str]] = None,
    ) -> AdherenceEvent:
        """Evaluate whether an action is permitted and record the event.

        Returns the created AdherenceEvent. If the action is blocked,
        the event carries decision=deny (or escalate) and reasoning that
        explains why; the caller SHOULD NOT proceed with the underlying
        skill call in that case.
        """
        binding = self.bindings.get(callee_base_url)
        if binding is None:
            raise RuntimeError(
                f"no consent binding for {callee_base_url}; call bind() first"
            )

        parsed = next(
            (p for p in binding.consent_record.parsed_claims if p.claim_id == claim_id),
            None,
        )
        claim = next(
            (c for c in binding.policy.claims if c.claim_id == claim_id), None
        )
        if parsed is None or claim is None:
            raise RuntimeError(
                f"claim_id {claim_id!r} not found in bound consent for "
                f"{callee_base_url}"
            )

        decision, reasoning = _evaluate(claim, parsed, action, context or {})

        event = AdherenceEvent(
            event_id=str(uuid.uuid4()),
            prev_event_id=binding.last_event_id,
            consent_record_id=binding.consent_record.record_id,
            action=action,
            clause_evaluated=clause_evaluated,
            claim_id=claim_id,
            decision=decision,
            reasoning=reasoning,
            timestamp=_now_iso(),
            context=context or {},
        )
        binding.last_event_id = event.event_id

        # POST to /acap/adherence on the callee.
        adherence_endpoint = f"{callee_base_url.rstrip('/')}/acap/adherence"
        resp = await self.http.post(
            adherence_endpoint, json=json.loads(event.model_dump_json())
        )
        resp.raise_for_status()
        return event

    async def aclose(self) -> None:
        await self.http.aclose()


def _evaluate(
    claim: PolicyClaim,
    parsed: ParsedClaim,
    action: str,
    context: dict[str, str],
) -> tuple[AdherenceDecision, str]:
    """Small deterministic decision function called before each skill.

    This is intentionally rule-based rather than LLM-backed: once a claim
    has been parsed (by the ClaimParser) at bind time, the per-action
    decision for THIS claim should be deterministic. The ClaimParser is
    where the LLM reasoning happens; here we just apply the result.
    """
    # If the caller disputed this claim, we never permit an action
    # governed by it (S5/S6 in the paper's TLA+ model).
    if parsed.disputed:
        return (
            AdherenceDecision.DENY,
            f"Action {action!r} is governed by disputed claim {claim.claim_id!r} "
            f"({claim.clause_ref}); caller disputed this clause during bind: "
            f"{parsed.dispute_reason or 'reason not recorded'}. Denying.",
        )

    # Apply the claim's rule_type.
    if claim.rule_type == RuleType.PROHIBITION:
        # Check constraint, if the constraint is satisfied the action
        # is blocked; if the constraint can be shown not to apply we
        # permit. For the demo we honour a simple `purpose != X` style
        # constraint encoded in context.
        if _constraint_matches(claim, context):
            return (
                AdherenceDecision.DENY,
                f"Action {action!r} matches prohibition {claim.clause_ref} "
                f"({claim.action} on {claim.asset}) under the current context "
                f"{context!r}. Denying.",
            )
        return (
            AdherenceDecision.PERMIT,
            f"Action {action!r} is governed by prohibition {claim.clause_ref} but "
            f"the prohibition's constraint does not apply under context {context!r}. "
            "Permitting.",
        )
    if claim.rule_type == RuleType.OBLIGATION:
        return (
            AdherenceDecision.PERMIT,
            f"Action {action!r} maps to obligation {claim.clause_ref}. Permitting.",
        )
    # permission
    return (
        AdherenceDecision.PERMIT,
        f"Action {action!r} is permitted under {claim.clause_ref}.",
    )


def _constraint_matches(claim: PolicyClaim, context: dict[str, str]) -> bool:
    """Minimal ODRL constraint evaluator for the demo.

    Handles `odrl:<left> is <right>` and `odrl:<left> isNot <right>`.
    A production implementation would use a real ODRL library.
    """
    if not claim.constraint:
        return True  # unconditional prohibition
    expr = claim.constraint.strip()
    for op, match_if_equal in (("isNot", False), ("is", True)):
        token = f" {op} "
        if token in expr:
            left, right = expr.split(token, 1)
            left = left.removeprefix("odrl:").strip()
            right = right.strip()
            if context.get(left) == right:
                return match_if_equal
            return not match_if_equal
    # Unknown constraint form, be conservative and treat as applicable.
    return True


# ───────────────────────────────────────────────────────────────────────
# Gemini-backed ClaimParser
# ───────────────────────────────────────────────────────────────────────


class GeminiClaimParser:
    """ClaimParser that uses Gemini to decide understanding + dispute."""

    PROMPT = """\
You are the consent-parsing module for an AI agent that is about to call
another agent. Your job is to look at ONE policy clause that the callee
agent is asking your agent to accept, and decide:

 1. Do you understand what the clause means? (understood: true/false)
 2. Does the clause conflict with the caller's declared intent?
    (disputed: true/false)
 3. If disputed, a one-sentence explanation of the conflict.

Caller intent: {intent}

Policy clause:
  clause_ref : {clause_ref}
  action     : {action}
  asset      : {asset}
  rule_type  : {rule_type}
  constraint : {constraint}

Respond with a JSON object exactly like:
{{"understood": true, "disputed": false, "dispute_reason": null}}
"""

    def __init__(self, model: str = "gemini-2.5-flash"):
        # Import lazily so that users who don't enable the demo extra
        # do not have to install google-genai.
        from google import genai

        self._client = genai.Client()
        self._model = model

    def parse(self, claim: PolicyClaim, caller_intent: str) -> ParsedClaim:
        prompt = self.PROMPT.format(
            intent=caller_intent,
            clause_ref=claim.clause_ref,
            action=claim.action,
            asset=claim.asset,
            rule_type=claim.rule_type.value,
            constraint=claim.constraint or "<none>",
        )
        resp = self._client.models.generate_content(
            model=self._model, contents=prompt
        )
        raw = resp.text.strip()
        # Strip code fences if the model added them.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:].lstrip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: if the model produced prose, treat the clause as
            # not understood so the human is escalated.
            return ParsedClaim(
                claim_id=claim.claim_id,
                understood=False,
                disputed=False,
                dispute_reason=None,
            )
        return ParsedClaim(
            claim_id=claim.claim_id,
            understood=bool(data.get("understood", False)),
            disputed=bool(data.get("disputed", False)),
            dispute_reason=data.get("dispute_reason"),
        )
