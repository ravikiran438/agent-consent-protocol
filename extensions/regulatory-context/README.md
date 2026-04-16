# Regulatory Context Extension

An extension to Anumati Core that propagates **jurisdictional
obligations** (GDPR, HIPAA, PCI-DSS, CCPA, EU AI Act, COPPA, …)
through the consent chain, independent of what any single party's
policy permits.

## The problem

None of HIPAA, GDPR, or PCI-DSS govern agents directly. They govern
the *organisations* behind the agents, covered entities, data
controllers, merchants, and the humans who operate them.

But the agent has to behave *as if* it were subject to the framework,
because the compliance obligation flows through delegation. A hospital
deploying an agent inherits its HIPAA obligations for anything the
agent handles, regardless of what the callee's `PolicyDocument`
permits or what the principal personally prefers.

The regulatory framework is a **floor** that neither the callee's
policy claims nor the principal's preferences can lower.

## The design direction

Add a `RegulatoryContext` field to both the `PolicyDocument`
(callee's compliance context) and the `ConsentRecord` (caller's
compliance context). Each context declares:

- **Framework**, which regime applies
- **Role**, the declaring party's role (data controller, covered
  entity, merchant, deployer)
- **Obligations**, structured constraints as (category, dimension)
  pairs with a minimum sensitivity level

When both parties declare regulatory contexts, the stricter constraint
wins. A principal who "doesn't care" about third-party sharing cannot
lower a callee's HIPAA §164.502(b) floor.

## Why a legal co-author is required before this ships

This extension makes claims that are *legal determinations*, not
protocol determinations. Before this extension can be published
normatively:

- A compliance engineer or healthcare-law specialist needs to review
  the HIPAA → (category, dimension) translation
- A data-protection lawyer needs to review the GDPR Art. 28 / 44-49 /
  22 mappings
- The EU AI Act claims need checking against the Article 50 deployer
  obligations

Without expert review, shipping this as a normative protocol extension
would be overreach.

## Why it's separated from Core

Anumati Core can be adopted today by any pair of agents. This extension
requires infrastructure that is jurisdiction-specific: maintained
obligation libraries, update processes when regulations change, and
legal review for each translation. That complexity shouldn't block
adoption of the core protocol.
