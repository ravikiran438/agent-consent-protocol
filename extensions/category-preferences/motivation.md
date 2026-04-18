# Category Preferences: Why This Extension Exists

This document explains the motivation for the category-preferences
extension to the Agent Consent and Adherence Protocol (ACAP). Section 1
describes why a boolean "I agree" does not survive contact with real
deployments. Section 2 describes why Core alone cannot carry the
asymmetry a principal actually feels. Section 3 describes our approach:
a two-axis sensitivity matrix that travels with the `ConsentRecord`.
Section 4 compares the design against alternatives we considered.
Section 5 fences off what this extension does not attempt.

## 1. The problem

ACAP Core records a principal's decision on each `PolicyClaim` as
`accepted`, `rejected`, or `conditional` with per-claim dispute flags.
The decision is uniform in weight: every claim is treated as equally
important.

In practice that is not how principals think.

A user uploading a passport photo to a travel booking agent cares a
great deal about how the photo is stored and almost not at all about
how their given name is retained. The same user at a cosmetic-surgery
consultation agent cares acutely about who can *access* the biometric
photo during the consultation, and even more about whether that photo
will leave the clinic relationship. The same user at a pharmacy has
no issue with prescription data being stored, because storage is the
point of the interaction, but would object strenuously to the same
data being forwarded to an advertising network.

So sensitivity has two properties Core does not capture: it is
*category-specific* (biometric is not like behavioral is not like
financial) and it is *dimension-specific* (storage is not like
third-party sharing is not like training data). It is also
*context-dependent* in the callee: the same category can be LOW at one
callee and HIGH at another, legitimately.

A principal who cannot express that asymmetry is a principal who is
being asked a question their own intuition already knows the answer to
but the protocol cannot carry.

## 2. Why core alone is insufficient

We considered extending Core with a per-claim sensitivity field. The
approach fails for three reasons.

First, sensitivity is not a property of the claim; it is a property of
the *principal's relationship to the data the claim concerns*. Two
callees can have identical `PolicyClaim` text and deserve very
different human reactions, because the category and the context are
different. Encoding sensitivity on the claim puts it on the wrong
object.

Second, the claim is written by the callee, not the principal. A
sensitivity flag on the claim is a flag the callee would set, which is
the same incentive problem we identified for the governance-tiering
extension. The callee benefits from downplaying sensitivity. The
principal's voice has to live somewhere the callee does not write.

Third, asymmetry is two-dimensional. Any single scalar on the claim
collapses (category, dimension) onto one axis, such that a principal
who feels differently about "store biometric" versus "share biometric"
has no way to say so. We tried the one-dimensional version on paper
and found ourselves consistently conflating "kind of data" with "kind
of operation" in the examples.

What Core cannot do is carry a two-axis, principal-authored, per-callee
expression of what matters. That is the gap this extension fills.

## 3. Our approach

We add a `category_preferences` matrix to the extension envelope that
travels alongside the `ConsentRecord`. The matrix has two axes:

  1. `DataCategory`, a closed vocabulary of nine values (biometric,
     health, financial, location, behavioral, identity, communications,
     minor-or-dependent, operational)
  2. `UsageDimension`, a closed vocabulary of eight values (storage,
     access, third-party sharing, automated decision, training,
     aggregation, cross-context use, deletion or portability)

The principal expresses a `CategorySensitivity` value, `LOW`, `MEDIUM`,
or `HIGH`, for each cell they care about. The matrix is sparse: the
principal only fills in the cells they have an opinion on. Absence of
an opinion resolves to `LOW`, on the reasoning that a principal who
has not declared a preference cannot be said to hold one.

Our approach has four practical properties that matter for deployment.

First, the matrix is *per-callee*, not global. A principal's attitude
toward health data at a pharmacy is not their attitude toward health
data at an advertising network, and the protocol should not force them
to express a global average that fits neither context. Each
`ConsentRecord` carries its own matrix, negotiated with that specific
callee.

Second, the resolver supports a *default row* per category. A
principal can say "biometric is HIGH everywhere" with one entry and
then override only the cells where that is wrong (for example, the
surgeon who needs ACCESS during consultation gets the override to
MEDIUM, while STORAGE and THIRD_PARTY_SHARING stay at HIGH). This
matches how principals actually reason: by default and exception,
not by filling in a 9x8 grid.

Third, the vocabularies are coarse on purpose. Nine categories and
eight dimensions are enough vocabulary for a human interface to
surface, such that a principal can set and review their preferences
without a training session. Fine-grained classification continues to
live in the [ODRL 2.2](https://www.w3.org/TR/odrl-model/)-aligned
`action` and `asset` fields on the claim. The matrix speaks the
human's language; the claim speaks the protocol's language; the
caller-side adapter translates between them.

Fourth, the matrix is a *caller-side signal*, not a callee-side
enforcement. The callee is not obligated to interpret the matrix, but
a caller that respects its principal will consult the matrix before
each action and record the consulted cell in the `AdherenceEvent`. So
an auditor walking the adherence trail can see not only what was
permitted, but which cell of the principal's sensitivity matrix the
caller consulted at the moment of the decision.

## 4. Alternatives considered

We considered four alternatives to the two-axis matrix before settling
on it.

**One-dimensional sensitivity tier per claim.** Each `PolicyClaim`
carries a `sensitivity` enum value declared by the principal at
consent time. Fails the test in Section 2: it puts the field on the
wrong object and collapses asymmetry. Rejected.

**Free-form natural-language preferences.** The principal writes a
paragraph describing what they care about, and a language model
interprets it at evaluation time. Appealing for expressivity, unworkable
for audit: two language models will interpret the same paragraph
differently, and the caller has no reproducible cell to record in the
adherence trail. We kept the vocabulary closed for that reason.

**Machine-learned preferences.** The caller observes the principal's
past decisions and infers a preference profile. This works for
recommendation but not for consent: the principal's stated preference,
not the caller's inferred model of it, is the legal ground truth. We
explicitly ruled inference out of scope.

**Categories only, no dimensions.** A one-axis matrix with only the
category vocabulary. Examples drove us off this quickly: "I feel
strongly about biometric" is not a sensible preference without saying
what operation is being performed on the biometric. Two axes are the
minimum.

## 5. Out of scope

This extension proposes a minimal base. It does not specify how a
caller's [ODRL 2.2](https://www.w3.org/TR/odrl-model/)-aligned
`action` and `asset` fields map to the (category, dimension) axes,
how a user interface elicits the matrix from the principal, how
preferences are ported from one callee to another (they are not, by
design), how the matrix interacts with machine-learned preference
inference, or how a caller negotiates matrix updates in a long-lived
relationship. Each of these is a real problem and each deserves its
own specification.

We expect two downstream consumers in particular. The
regulatory-context extension uses the same (category, dimension) grid
as the encoding surface for jurisdictional floors, such that the
effective sensitivity for a cell is the strictest of the principal's
preference, the callee's declared compliance posture, and the
applicable regulatory framework. The governance-tiering extension
layers on top: a claim affecting a `HIGH` cell is a candidate for
automatic `HUMAN_REQUIRED` escalation regardless of the structural
signals on the policy diff. A guardian extension targeted at
vulnerable-population protection, including the `MINOR_OR_DEPENDENT`
category, is a natural downstream consumer that composes all three.

## References

The idea that sensitivity shifts with the setting of the data exchange
(the same health record is not equally sensitive at a pharmacy and at
an advertising network) is rooted in Nissenbaum's framework of
[contextual integrity](https://en.wikipedia.org/wiki/Contextual_integrity).
The ODRL vocabulary this extension's `action` and `asset` interop
points reference is the [W3C ODRL 2.2 Information Model](https://www.w3.org/TR/odrl-model/).
For the Core ACAP specification this extension builds on, see the
paper at [Zenodo DOI 10.5281/zenodo.19606339](https://doi.org/10.5281/zenodo.19606339).
