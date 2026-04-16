# Category Preferences Extension

An extension to Anumati Core that lets a human principal express
**asymmetric sensitivity** across two orthogonal axes: the *category*
of data (biometric, health, financial, …) and the *dimension* of use
(storage, access, third-party sharing, training, …).

## The problem

Anumati Core's `ConsentRecord` treats every `PolicyClaim` as equally
important to the human principal. In practice they are not.

A user uploading a passport photo cares much more about how the photo
is stored than about how their name is retained. The same user at a
pharmacy has no issue with prescription data being recorded, but would
strongly object to that data being shared with an advertising network.

Sensitivity is context-dependent. A single "I agree" flag can't express
this.

## The design direction

Add a `category_preferences` matrix to the `ConsentRecord`. The
principal expresses a sensitivity level, `LOW`, `MEDIUM`, or `HIGH`,
for each (category, dimension) pair. The matrix travels with the
consent record, not a global profile, because preferences legitimately
differ per callee.

Example (cosmetic surgery app):

|            | Storage | Access | 3P Sharing | Training |
|------------|---------|--------|------------|----------|
| Biometric  | HIGH    | MEDIUM | HIGH       | HIGH     |
| Health     | MEDIUM  | LOW    | HIGH       | HIGH     |
| Financial  | LOW     | LOW    | MEDIUM     | HIGH     |

Same principal at a pharmacy would set `Health × Storage` to `LOW`
because that's the purpose of the interaction, but keep
`Health × Third-Party Sharing` at `HIGH`.

## Proposed vocabularies

**Categories (9):** biometric, health, financial, location, behavioural,
identity, communications, minor/dependent, operational.

**Dimensions (8):** storage, access, third-party sharing, automated
decision, training, aggregation, cross-context use, deletion/portability.

Both vocabularies are intentionally coarse, fine-grained classification
stays in the ODRL-aligned `action` and `asset` fields. The goal is a
vocabulary a human can reason about without understanding ODRL.

## Why it's separated from Core

Preference matrices are a UX / consent-design concern, not a protocol
concern. Anumati Core defines what is recorded; this extension defines
how a human expresses what they care about.

The matrix design has not been validated empirically. A user study
would be needed before normalising a specific category/dimension
taxonomy.
