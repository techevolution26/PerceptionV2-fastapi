# Perception — Stage 4 release notes

## Professional identity

Stage 4 replaces the product's dependency on a free-form profession string with a structured professional taxonomy.

- 33 industries
- 202 professional roles
- multiple industries per user
- multiple professional roles per user
- one primary professional role
- verified professional roles tracked separately
- stable role/industry codes are persisted; labels and icon presentation remain client-controlled

A professional badge communicates the selected professional identity. A verification badge communicates that Perception has reviewed and approved the identity.

## Verification policy

Payment does **not** grant verification.

A subscription plan may include `verification_included`, which means the user is eligible to submit a professional verification application. The application remains subject to Super Admin review. Approval/rejection is recorded in the administrative audit trail.

## Topic onboarding

Topic selection is intentionally optional. A new user can continue to the feed without following a topic. If they continue with zero followed topics, a persistent feed reminder points them back to Topics. The reminder disappears once at least one topic is followed.

## Database migration

Run the new migration before using structured professional identity fields:

```bash
alembic upgrade head
```

Migration: `0006_professional_identity_taxonomy`

No existing profession data is deleted. Existing free-form values remain as legacy profile data until the user selects structured professional identities.

## Stage 4H — Comment Intelligence Foundation

- Perception analytics now distinguishes author `creator_analytics` from non-author `conversation_intelligence`.
- Non-authors can open the analytics/intelligence surface without receiving the author's private analytics subscription gate.
- Aggregate audience intelligence remains subject to the 5-participant suppression threshold and does not expose individual identities or cities.
- Semantic analysis is explicitly marked unavailable until the comment-intelligence layer is implemented; no fabricated sentiment, stance, or theme results are shown.
