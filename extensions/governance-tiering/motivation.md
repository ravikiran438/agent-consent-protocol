# Governance Tiering: Why This Extension Exists

This document explains the motivation for the governance-tiering
extension to the Agent Consent and Adherence Protocol (ACAP). Section 1
describes the alert-fatigue problem that appears the moment ACAP Core
is deployed at scale. Section 2 describes why Core alone cannot solve
it without giving up something we want to keep. Section 3 describes our
approach: a tiered escalation model with an optional supervisory
governance agent. Section 4 compares the approach against alternatives
we considered. Section 5 fences off what this extension does not
attempt.

## 1. The problem

ACAP Core requires a new `ConsentRecord` on every `PolicyDocument`
version bump. This is what gives the protocol its legal integrity: a
caller cannot silently drift past a policy change, because every bump
forces the caller to parse the new document and record a fresh decision
for every claim. The linked-list structure of the consent chain carries
the full history of what was accepted, when, and by which principal.

So the invariant is load-bearing for audit. It is also load-bearing for
alert fatigue.

In a deployment where a single human principal is served by five
calling agents, each of which talks to twenty callees, and each callee
publishes a minor policy revision once a week, the principal is
staring at one hundred re-consent prompts every week. Most of those
prompts are trivial: a typo fix in the natural-language policy, a
clause renumbering, a tightening of an already-restrictive constraint.
Under the Core invariant, every one of them still produces a
`ConsentRecord`. Under reasonable user-interface conventions, every
one of them still interrupts the principal.

Agents operating under the [EU AI Act's Article 50](https://artificialintelligenceact.eu/article/50/)
transparency obligations face a sharper version of this. The Act
requires the deployer to inform the affected person that they are
interacting with an AI system, and for high-risk cases, to surface
the terms under which automated decisions are being made. A deployment that produces
one hundred modal dialogs per week satisfies the letter of the
obligation and defeats its intent. The principal learns to click
through.

We have seen this pattern in older terms-of-service systems. When the
cost of reading is high and the cost of clicking is zero, people
click. The information-theoretic content of the consent collapses to
approximately zero. That is the outcome ACAP Core was designed to
prevent, and it is the outcome an honest implementation of Core will
produce in the absence of tiering.

## 2. Why core alone is insufficient

One response to the alert-fatigue problem is to relax the Core
invariant: allow the caller to skip re-consent on "minor" changes. We
considered this and rejected it. The core invariant is what makes
proof-of-adherence distinct from proof-of-acceptance, such that
removing it rebuilds the click-through model every online service
already has.

A second response is to let the calling agent decide on its own
whether a change is minor and skip the re-consent when the agent
judges it immaterial. This is worse. Callers have incentives to
minimize interruption to their principal; they are not neutral. The
party that would be judging materiality is the same party that
benefits from judging generously. Without an external check the
judgment is unauditable.

A third response is to require the callee to pre-classify each version
bump as major or minor, and let callers honor the classification. This
moves the incentive problem to a different actor who also has a stake
in the answer. Callees benefit from classifying their changes as minor
because it reduces the cost of deployment. The classification is
again unauditable.

What Core cannot do alone is produce an auditable classification from
a party whose incentives are aligned with the principal. That is the
gap this extension fills.

## 3. Our approach

We propose a supervisory agent, the *governance agent*, whose sole job
is to classify policy-version bumps into one of three tiers:

  1. `auto_approved`, an immaterial change (for example, clause
     renumbering, typo fixes, metadata-only bumps) where the governance
     agent proceeds on the principal's behalf without prompting
  2. `governance_reviewed`, a change material enough to record but
     within a pre-declared delegation envelope where the governance
     agent acts on the principal's behalf with an audit entry
  3. `human_required`, a change where the governance agent blocks the
     re-consent flow until the principal reviews and decides

The governance agent's classification decision is itself recorded on
the `ConsentRecord` as an `EscalationAssessment`, signed, timestamped,
and carrying the structured `MaterialitySignal` list that informed the
tier choice. So an auditor walking the consent chain can see not only
what was accepted, but who decided the acceptance could proceed without
the principal, and on what basis.

Our approach has four practical properties that matter for deployment.

First, the governance agent operates under a *meta-policy* declared by
the principal. The meta-policy fixes which classes of change may be
auto-approved and which must escalate. A principal who wants to see
every change declares a meta-policy with an empty auto-approval set,
such that the governance agent behaves as a pass-through. A principal
willing to delegate everything short of a rule-type inversion declares
a permissive meta-policy. The two extremes collapse to "Core with a
logging wrapper" and "fully delegated", and the interesting middle is
where most deployments will live.

Second, the classification is derived from structural signals on the
policy diff, not from the governance agent's general judgment. The
reference implementation recognizes six signals: `new_claim`,
`removed_claim`, `modified_claim`, `rule_type_inversion`,
`constraint_relaxed`, `escalate_on_deny_added`. Each signal is a
mechanical check against the diff, such that two conformant
implementations will agree on the signals fired even when they disagree
on how to render the summary prose. Downstream agents that want
semantic reasoning (for example, a language-model-assisted classifier
distinguishing "tightened" from "relaxed" constraints) layer on top of
the structural floor rather than replacing it.

Third, the tier choice is a total function of the fired signals. Given
the same diff and the same meta-policy, two governance agents must
produce the same tier. This matters for audit: an auditor can re-run
the classification from the diff and the meta-policy without replaying
the agent's internal reasoning.

Fourth, the `GovernanceReview` state is formally modeled. The ACAP
consent-lifecycle TLA+ specification (`ConsentLifecycle.tla`) already
includes the state together with two invariants specific to this
extension: S8 (`GovernanceAlwaysReviews`, no re-consent bypasses the
governance agent) and S9 (`HumanRequiredHonoured`, a `human_required`
tier blocks the chain until the principal acts). TLC verifies both
under bounded model checking.

## 4. Alternatives considered

We considered four alternatives to the governance-agent model before
settling on it.

**Time-windowed auto-approval.** A calling agent auto-approves any
bump within a rolling N-day window without review, then surfaces the
aggregate to the principal periodically. This trades audit granularity
for throughput. We rejected it because the per-change decision is
where the legal exposure lives, such that batching removes exactly the
information the audit chain is for.

**Reputation-weighted approval.** A callee with a long track record of
minor-only bumps gets its bumps auto-approved, while a new or noisy
callee goes to the principal. This shifts the problem to reputation
accounting, which has its own well-known attack surfaces and is itself
a separate protocol concern. We kept it out of scope.

**Principal-local classification.** The principal's own user agent
classifies bumps rather than delegating to a separate governance
agent. This collapses the governance-agent role into the calling
agent, which is exactly the incentive problem from Section 2. We kept
the actors separate.

**Callee-declared materiality.** The callee declares each bump as
major or minor in the `PolicyDocument` metadata, and callers honor the
declaration. Same incentive problem on the other side of the
relationship. Out.

## 5. Out of scope

This extension proposes a minimal base. It does not standardize how
the governance agent is discovered from the caller's `AgentCard`, how
governance agents authenticate to principals, how meta-policies are
expressed in machine-readable form, how a language-model-assisted
semantic classifier distinguishes relaxation from tightening in
natural language, how governance agents are economically compensated,
or how their classifications are ranked for quality. Each of these is
a real problem and each deserves its own specification.

We expect downstream extensions, in particular a guardian extension
targeted at vulnerable-population protection, to build on this base.
Commercial implementations that want to monetize governance-agent
services, or larger working-group efforts that want to deepen the
formal treatment, have a clean seam to extend from without
renegotiating the state machine or the chain invariants.

## References

The closest prior art is the Governance-as-a-Service framework
(Gaurav et al., [arXiv:2508.18765](https://arxiv.org/abs/2508.18765)),
which proposes an external governance agent supervising other agents
at runtime. The [AIGA Internet-Draft](https://datatracker.ietf.org/doc/draft-aylward-aiga-1/)
proposes complementary accountability primitives. For the Core ACAP
specification this extension builds on, see the paper at
[Zenodo DOI 10.5281/zenodo.19606339](https://doi.org/10.5281/zenodo.19606339).
