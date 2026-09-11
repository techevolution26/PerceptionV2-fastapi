# Perception — Privacy & Data Classification

## Purpose

This document defines the minimum privacy boundary for Perception's production release.
It is a product/engineering control document, not legal advice.

## Data classes

### Public social content

Content intentionally published into the public Perception conversation surface:

- public perception body
- public topic metadata
- public comment/reply body
- public avatar and public profile identity fields
- public professional identity fields deliberately exposed by the product

These fields may be returned by public endpoints when the account is active.

### Private account data

Never expose through public identity/content contracts:

- email
- password hash
- JWT/token state
- Google OAuth subject
- billing customer identifiers
- account role
- token version
- analytics specialties
- primary analytics topic
- private analytical geography
- account activity flags

### Aggregate intelligence

Only expose aggregate intelligence when the applicable minimum sample is met.
The current minimum is **5 analyzed observations**.

Never expose:

- commenter identities
- participant names
- participant IDs
- individual psychological/personality scores
- inferred protected traits
- city-level aggregate intelligence
- causal claims unsupported by evidence

### AI processing data

The controlled AI worker may send only the minimum discussion context required to analyze:

- perception topic
- perception text
- comment text

It must not send participant identity or profile attributes.

External AI processing is **disabled by default** and requires an explicit production configuration gate.

The provider request uses `store=false`, but this is not treated as equivalent to zero retention. OpenAI's current API privacy documentation says API data is not used to train models by default, while some API inputs/outputs may be retained for abuse monitoring for up to 30 days unless an eligible zero-data-retention arrangement applies. Production privacy documentation must therefore disclose the external processor and applicable retention terms.

## Access model

### Observer

Free conversation intelligence may expose aggregate conversation findings, subject to the minimum sample and evidence-governance rules.

Creator-only measurements such as views, shares, engagement rate, and daily activity are not exposed to observers.

### Author / creator analytics

Creator analytics is restricted to the authenticated perception owner and the applicable analytics entitlement.

### Comparative intelligence

Comparative intelligence is restricted to authenticated users comparing their own authored perceptions and requires analytics access.

### AI response labels

`ai_analysis_status` is not a public field in practice. It is returned only to the authorized owner path with analytics access. Other viewers receive `null`.

## Privacy-by-design rules

1. Deny by default.
2. Collect/process only what the feature requires.
3. Do not return private fields merely because the ORM object contains them.
4. Enforce authorization server-side; mobile flags are not security boundaries.
5. Suppress small samples rather than attempting to infer missing information.
6. Keep participant identity separate from aggregate intelligence.
7. Do not infer sensitive characteristics.
8. Do not log passwords, access tokens, secrets, or unnecessary personal data.
9. Keep external AI processing opt-in at the production configuration layer.
10. Review third-party processors and data-transfer safeguards before production.

## Release evidence required

Before production release, retain evidence for:

- database access restrictions
- encrypted production connections/storage where provided by infrastructure
- production CORS allowlist
- TLS/HTTPS for public services
- secret storage outside source control
- backup and restore controls
- retention/deletion procedures
- third-party processor inventory and agreements where required
- privacy notice and terms presented to users
- breach response procedure
- production logs and access restrictions
- test evidence for owner/non-owner analytics isolation

## Important limitation

Automated application tests cannot prove that the hosting provider, database, Redis instance, object storage, CI/CD system, administrator accounts, or third-party processor are configured correctly. Those controls require an infrastructure/security review before production launch.
