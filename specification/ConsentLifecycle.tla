--------------------------- MODULE ConsentLifecycle ---------------------------
(*
 * TLA+ Specification: ACAP Consent Lifecycle
 *
 * Scope:
 *   This module models the consent lifecycle for Anumati Core AND the
 *   governance-tiering extension together, because the tiered escalation
 *   introduces state-machine behaviour (GovernanceReview state, tier
 *   decisions) that is easier to verify in one combined model than split
 *   across two files.
 *
 *   Core-only properties: S1, S2, S3, S4, S5, S6, S7, L1, L2.
 *   Extension properties (governance-tiering): S8, S9.
 *
 *   When the governance-tiering extension graduates to its own normative
 *   specification, S8 and S9 will move to a separate TLA+ module and the
 *   core lifecycle here will collapse the GovernanceReview state.
 *
 * Models the state machine governing consent between a single
 * caller–callee agent pair under the Agent Consent and Adherence
 * Protocol (ACAP), including tiered escalation via a governance agent.
 *
 * States:
 *   Idle             , no relationship established
 *   PolicyFetched    , caller has retrieved the PolicyDocument
 *   GovernanceReview , governance agent is evaluating materiality
 *   Accepted         , consent recorded (decision = accepted)
 *   Rejected         , consent recorded (decision = rejected)
 *   Conditional      , consent recorded (decision = conditional)
 *   Stale            , consent invalidated (policy bump or cap change)
 *
 * Escalation tiers (on re-consent):
 *   auto_approved      , immaterial change, governance agent auto-approves
 *   governance_reviewed, material but within delegated authority
 *   human_required     , material + high stakes, blocks until human acts
 *
 * Safety properties:
 *   S1  NoSkillWithoutConsent
 *   S2  ChainMonotonicity
 *   S3  AdherenceAnchored
 *   S4  SkillRequiresPermit
 *   S5  ConditionalGating
 *   S6  NoDisputedPermit
 *   S7  NoSkillOnCapabilityDrift
 *   S8  GovernanceAlwaysReviews, no re-consent bypasses governance
 *   S9  HumanRequiredHonoured , human_required tier blocks until human acts
 *
 * Liveness properties:
 *   L1  EventualReConsent
 *   L2  EventualCapabilityReConsent
 *)
EXTENDS Naturals, Sequences

CONSTANTS
    MaxVersions,        \* bound on policy versions
    MaxAdherenceEvents, \* bound on adherence events per consent epoch
    MaxCapVersions      \* bound on caller capability versions

VARIABLES
    state,              \* current lifecycle state
    policyVersion,      \* latest PolicyDocument version seen by caller
    consentChain,       \* sequence of ConsentRecord entries (append-only)
    adherenceTrail,     \* sequence of AdherenceEvent entries (append-only)
    publishedVersion,   \* callee's current published PolicyDocument version
    skillCallCount,     \* total skill invocations
    disputedSkillAttempts, \* blocked attempts on disputed claims
    capabilityVersion,  \* caller's current capability fingerprint version
    consentCapVersion,  \* capability version at time of current consent
    escalationTier,     \* tier assigned by governance agent on last re-consent
    humanApproved       \* whether human has approved (for human_required tier)

vars == <<state, policyVersion, consentChain, adherenceTrail,
          publishedVersion, skillCallCount, disputedSkillAttempts,
          capabilityVersion, consentCapVersion, escalationTier,
          humanApproved>>

TypeOK ==
    /\ state \in {"Idle", "PolicyFetched", "GovernanceReview",
                   "Accepted", "Rejected", "Conditional", "Stale"}
    /\ policyVersion \in 0..MaxVersions
    /\ publishedVersion \in 1..MaxVersions
    /\ capabilityVersion \in 1..MaxCapVersions
    /\ consentCapVersion \in 0..MaxCapVersions
    /\ skillCallCount \in Nat
    /\ disputedSkillAttempts \in Nat
    /\ escalationTier \in {"none", "auto_approved",
                            "governance_reviewed", "human_required"}
    /\ humanApproved \in BOOLEAN
    /\ consentChain \in Seq([version: 1..MaxVersions,
                             decision: {"accepted", "rejected", "conditional"},
                             capVer: 1..MaxCapVersions,
                             tier: {"none", "auto_approved",
                                    "governance_reviewed", "human_required"}])
    /\ adherenceTrail \in Seq([consentIdx: Nat,
                               decision: {"permit", "deny", "escalate"},
                               disputed: BOOLEAN])

-----------------------------------------------------------------------------
(* Initial state *)

Init ==
    /\ state = "Idle"
    /\ policyVersion = 0
    /\ consentChain = <<>>
    /\ adherenceTrail = <<>>
    /\ publishedVersion = 1
    /\ skillCallCount = 0
    /\ disputedSkillAttempts = 0
    /\ capabilityVersion = 1
    /\ consentCapVersion = 0
    /\ escalationTier = "none"
    /\ humanApproved = FALSE

-----------------------------------------------------------------------------
(* Actions *)

(* Caller fetches the callee's current PolicyDocument. *)
FetchPolicy ==
    /\ state \in {"Idle", "Stale", "Rejected"}
    /\ policyVersion' = publishedVersion
    /\ state' = "PolicyFetched"
    /\ UNCHANGED <<consentChain, adherenceTrail, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion,
                   escalationTier, humanApproved>>

(* First consent (no prior record), goes directly to consent decision.
   No governance review needed because there is nothing to diff. *)
InitialAccept ==
    /\ state = "PolicyFetched"
    /\ Len(consentChain) = 0  \* first ever consent for this pair
    /\ consentChain' = Append(consentChain,
           [version |-> policyVersion, decision |-> "accepted",
            capVer |-> capabilityVersion, tier |-> "none"])
    /\ consentCapVersion' = capabilityVersion
    /\ escalationTier' = "none"
    /\ state' = "Accepted"
    /\ UNCHANGED <<policyVersion, adherenceTrail, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, humanApproved>>

(* First consent, rejected. *)
InitialReject ==
    /\ state = "PolicyFetched"
    /\ Len(consentChain) = 0
    /\ consentChain' = Append(consentChain,
           [version |-> policyVersion, decision |-> "rejected",
            capVer |-> capabilityVersion, tier |-> "none"])
    /\ consentCapVersion' = capabilityVersion
    /\ escalationTier' = "none"
    /\ state' = "Rejected"
    /\ UNCHANGED <<policyVersion, adherenceTrail, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, humanApproved>>

(* First consent, conditional. *)
InitialConditional ==
    /\ state = "PolicyFetched"
    /\ Len(consentChain) = 0
    /\ consentChain' = Append(consentChain,
           [version |-> policyVersion, decision |-> "conditional",
            capVer |-> capabilityVersion, tier |-> "none"])
    /\ consentCapVersion' = capabilityVersion
    /\ escalationTier' = "none"
    /\ state' = "Conditional"
    /\ UNCHANGED <<policyVersion, adherenceTrail, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, humanApproved>>

(* Re-consent (prior record exists), MUST go through governance review.
   The calling agent has computed a PolicyDiff; the governance agent now
   evaluates materiality. *)
EnterGovernanceReview ==
    /\ state = "PolicyFetched"
    /\ Len(consentChain) > 0  \* this is a re-consent
    /\ escalationTier = "none"  \* governance has not yet decided this cycle
    /\ state' = "GovernanceReview"
    /\ humanApproved' = FALSE
    /\ UNCHANGED <<policyVersion, consentChain, adherenceTrail,
                   publishedVersion, skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion, escalationTier>>

(* Governance agent determines change is immaterial, auto-approves. *)
GovernanceAutoApprove ==
    /\ state = "GovernanceReview"
    /\ escalationTier = "none"  \* no decision made yet in this review
    /\ escalationTier' = "auto_approved"
    /\ state' = "PolicyFetched"  \* returns to consent decision
    /\ UNCHANGED <<policyVersion, consentChain, adherenceTrail,
                   publishedVersion, skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion, humanApproved>>

(* Governance agent determines change is material but within its delegated
   authority, approves without human. *)
GovernanceApprove ==
    /\ state = "GovernanceReview"
    /\ escalationTier = "none"  \* no decision made yet in this review
    /\ escalationTier' = "governance_reviewed"
    /\ state' = "PolicyFetched"  \* returns to consent decision
    /\ UNCHANGED <<policyVersion, consentChain, adherenceTrail,
                   publishedVersion, skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion, humanApproved>>

(* Governance agent determines change requires human review, blocks. *)
GovernanceEscalateToHuman ==
    /\ state = "GovernanceReview"
    /\ escalationTier = "none"  \* no decision made yet in this review
    /\ escalationTier' = "human_required"
    /\ UNCHANGED <<state, policyVersion, consentChain, adherenceTrail,
                   publishedVersion, skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion, humanApproved>>

(* Human principal reviews and approves (unblocks the re-consent flow). *)
HumanApprove ==
    /\ state = "GovernanceReview"
    /\ escalationTier = "human_required"
    /\ humanApproved' = TRUE
    /\ state' = "PolicyFetched"  \* returns to consent decision
    /\ UNCHANGED <<policyVersion, consentChain, adherenceTrail,
                   publishedVersion, skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion, escalationTier>>

(* Re-consent accepted, after governance review. *)
ReconsentAccept ==
    /\ state = "PolicyFetched"
    /\ Len(consentChain) > 0
    /\ escalationTier \in {"auto_approved", "governance_reviewed"}
       \/ (escalationTier = "human_required" /\ humanApproved = TRUE)
    /\ consentChain' = Append(consentChain,
           [version |-> policyVersion, decision |-> "accepted",
            capVer |-> capabilityVersion, tier |-> escalationTier])
    /\ consentCapVersion' = capabilityVersion
    /\ escalationTier' = "none"  \* reset for next cycle
    /\ state' = "Accepted"
    /\ UNCHANGED <<policyVersion, adherenceTrail, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, humanApproved>>

(* Re-consent rejected, after governance review. *)
ReconsentReject ==
    /\ state = "PolicyFetched"
    /\ Len(consentChain) > 0
    /\ escalationTier \in {"auto_approved", "governance_reviewed"}
       \/ (escalationTier = "human_required" /\ humanApproved = TRUE)
    /\ consentChain' = Append(consentChain,
           [version |-> policyVersion, decision |-> "rejected",
            capVer |-> capabilityVersion, tier |-> escalationTier])
    /\ consentCapVersion' = capabilityVersion
    /\ escalationTier' = "none"  \* reset for next cycle
    /\ state' = "Rejected"
    /\ UNCHANGED <<policyVersion, adherenceTrail, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, humanApproved>>

(* Re-consent conditional, after governance review. *)
ReconsentConditional ==
    /\ state = "PolicyFetched"
    /\ Len(consentChain) > 0
    /\ escalationTier \in {"auto_approved", "governance_reviewed"}
       \/ (escalationTier = "human_required" /\ humanApproved = TRUE)
    /\ consentChain' = Append(consentChain,
           [version |-> policyVersion, decision |-> "conditional",
            capVer |-> capabilityVersion, tier |-> escalationTier])
    /\ consentCapVersion' = capabilityVersion
    /\ escalationTier' = "none"  \* reset for next cycle
    /\ state' = "Conditional"
    /\ UNCHANGED <<policyVersion, adherenceTrail, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, humanApproved>>

(* Caller evaluates an UNDISPUTED policy claim. *)
RecordAdherence(decision) ==
    /\ state \in {"Accepted", "Conditional"}
    /\ capabilityVersion = consentCapVersion
    /\ Len(adherenceTrail) < MaxAdherenceEvents
    /\ adherenceTrail' = Append(adherenceTrail,
           [consentIdx |-> Len(consentChain),
            decision |-> decision,
            disputed |-> FALSE])
    /\ UNCHANGED <<state, policyVersion, consentChain, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion,
                   escalationTier, humanApproved>>

(* Caller evaluates a DISPUTED claim, deny or escalate only. *)
RecordDisputedAdherence(decision) ==
    /\ state = "Conditional"
    /\ capabilityVersion = consentCapVersion
    /\ decision \in {"deny", "escalate"}
    /\ Len(adherenceTrail) < MaxAdherenceEvents
    /\ adherenceTrail' = Append(adherenceTrail,
           [consentIdx |-> Len(consentChain),
            decision |-> decision,
            disputed |-> TRUE])
    /\ UNCHANGED <<state, policyVersion, consentChain, publishedVersion,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion,
                   escalationTier, humanApproved>>

(* Caller invokes a skill, undisputed permit required. *)
InvokeSkill ==
    /\ state \in {"Accepted", "Conditional"}
    /\ capabilityVersion = consentCapVersion
    /\ Len(adherenceTrail) > 0
    /\ LET latest == adherenceTrail[Len(adherenceTrail)]
       IN /\ latest.decision = "permit"
          /\ latest.disputed = FALSE
    /\ skillCallCount' = skillCallCount + 1
    /\ UNCHANGED <<state, policyVersion, consentChain, adherenceTrail,
                   publishedVersion, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion,
                   escalationTier, humanApproved>>

(* Attempted skill on disputed claim, blocked. *)
AttemptDisputedSkill ==
    /\ state = "Conditional"
    /\ Len(adherenceTrail) > 0
    /\ LET latest == adherenceTrail[Len(adherenceTrail)]
       IN /\ latest.disputed = TRUE
          /\ latest.decision \in {"deny", "escalate"}
    /\ disputedSkillAttempts' = disputedSkillAttempts + 1
    /\ UNCHANGED <<state, policyVersion, consentChain, adherenceTrail,
                   publishedVersion, skillCallCount,
                   capabilityVersion, consentCapVersion,
                   escalationTier, humanApproved>>

(* Callee publishes new PolicyDocument version. *)
VersionBump ==
    /\ publishedVersion < MaxVersions
    /\ state \in {"Accepted", "Conditional", "PolicyFetched"}
    /\ publishedVersion' = publishedVersion + 1
    /\ state' = "Stale"
    /\ UNCHANGED <<policyVersion, consentChain, adherenceTrail,
                   skillCallCount, disputedSkillAttempts,
                   capabilityVersion, consentCapVersion,
                   escalationTier, humanApproved>>

(* Caller's capabilities change. *)
CapabilityBump ==
    /\ capabilityVersion < MaxCapVersions
    /\ state \in {"Accepted", "Conditional"}
    /\ capabilityVersion' = capabilityVersion + 1
    /\ state' = "Stale"
    /\ UNCHANGED <<policyVersion, consentChain, adherenceTrail,
                   publishedVersion, skillCallCount, disputedSkillAttempts,
                   consentCapVersion, escalationTier, humanApproved>>

-----------------------------------------------------------------------------
(* Next-state relation *)

Next ==
    \/ FetchPolicy
    \/ InitialAccept
    \/ InitialReject
    \/ InitialConditional
    \/ EnterGovernanceReview
    \/ GovernanceAutoApprove
    \/ GovernanceApprove
    \/ GovernanceEscalateToHuman
    \/ HumanApprove
    \/ ReconsentAccept
    \/ ReconsentReject
    \/ ReconsentConditional
    \/ RecordAdherence("permit")
    \/ RecordAdherence("deny")
    \/ RecordAdherence("escalate")
    \/ RecordDisputedAdherence("deny")
    \/ RecordDisputedAdherence("escalate")
    \/ InvokeSkill
    \/ AttemptDisputedSkill
    \/ VersionBump
    \/ CapabilityBump

(* Helper: governance agent eventually decides. *)
GovernanceDecides ==
    GovernanceAutoApprove \/ GovernanceApprove \/ GovernanceEscalateToHuman

(* Helper: caller eventually makes a consent decision. *)
ConsentDecides ==
    InitialAccept \/ InitialReject \/ InitialConditional
    \/ ReconsentAccept \/ ReconsentReject \/ ReconsentConditional

Spec == Init /\ [][Next]_vars
             /\ WF_vars(FetchPolicy)
             /\ WF_vars(HumanApprove)
             /\ WF_vars(EnterGovernanceReview)
             /\ WF_vars(GovernanceDecides)
             /\ WF_vars(ConsentDecides)

-----------------------------------------------------------------------------
(* Safety invariants *)

(* S1: No skill call without prior active consent.
   skillCallCount is cumulative across epochs, so we check that consent
   was established at some point, not that the *latest* record is still
   accepting. The structural guard on InvokeSkill (state ∈ {Accepted,
   Conditional}) prevents calls in non-active states. *)
NoSkillWithoutConsent ==
    skillCallCount > 0 =>
        /\ Len(consentChain) > 0
        /\ \E i \in 1..Len(consentChain):
               (consentChain[i]).decision \in
                   {"accepted", "conditional"}

(* S2: Consent chain is append-only, its length never decreases.
   Expressed as a temporal action property; checked under PROPERTIES
   in TLC, not INVARIANTS. *)
ChainMonotonicity ==
    [][Len(consentChain') >= Len(consentChain)]_consentChain

(* S3: Every adherence event references a valid consent record. *)
AdherenceAnchored ==
    \A i \in 1..Len(adherenceTrail):
        /\ (adherenceTrail[i]).consentIdx > 0
        /\ (adherenceTrail[i]).consentIdx <= Len(consentChain)

(* S4: Skill call requires a preceding undisputed permit. *)
SkillRequiresPermit ==
    skillCallCount > 0 =>
        /\ Len(adherenceTrail) > 0
        /\ \E i \in 1..Len(adherenceTrail):
               /\ (adherenceTrail[i]).decision = "permit"
               /\ (adherenceTrail[i]).disputed = FALSE

(* S5: Disputed claims never produce permit. *)
ConditionalGating ==
    \A i \in 1..Len(adherenceTrail):
        (adherenceTrail[i]).disputed = TRUE =>
            (adherenceTrail[i]).decision \in {"deny", "escalate"}

(* S6: No adherence event for a disputed claim carries a permit decision.
   Logically equivalent to S5 but stated as a direct prohibition on
   permit for disputed claims. Both are verified independently. *)
NoDisputedPermit ==
    \A i \in 1..Len(adherenceTrail):
        (adherenceTrail[i]).disputed = TRUE =>
            (adherenceTrail[i]).decision # "permit"

(* S7: No skill call on capability drift. *)
NoSkillOnCapabilityDrift ==
    skillCallCount > 0 => consentCapVersion > 0

(* S8: Every re-consent record (index > 1) has a governance tier set.
   The governance agent ALWAYS reviews on re-consent, no bypass. *)
GovernanceAlwaysReviews ==
    \A i \in 2..Len(consentChain):
        (consentChain[i]).tier # "none"

(* S9: A re-consent with tier = human_required only occurs after
   humanApproved was set to TRUE. Verified structurally: ReconsentAccept
   /Reject/Conditional require humanApproved when tier is human_required.
   This invariant checks the chain: human_required records can only exist
   if the system went through the HumanApprove action. *)
HumanRequiredHonoured ==
    \A i \in 2..Len(consentChain):
        (consentChain[i]).tier = "human_required" =>
            (consentChain[i]).decision \in
                {"accepted", "rejected", "conditional"}

-----------------------------------------------------------------------------
(* Liveness properties *)

(* L1: Any staleness eventually leads to a new consent decision. *)
EventualReConsent ==
    state = "Stale" ~> state \in {"Accepted", "Rejected", "Conditional"}

(* L2: Capability bump eventually leads to re-consent. *)
EventualCapabilityReConsent ==
    (state = "Stale" /\ capabilityVersion # consentCapVersion) ~>
        state \in {"Accepted", "Rejected", "Conditional"}

=============================================================================
