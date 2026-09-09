# Stage 4H.7 Hardening Pass

This pass keeps the Stage 4H.7 longitudinal-intelligence contract intact while correcting boundary semantics discovered during frontend review.

## Profile and identity boundaries

- Professional identity is managed only through the structured professional-identity flow.
- Professional verification reviews professional identity only. Analytics topics are not part of a verification application. Legacy topic columns remain in the persistence model for compatibility but new applications write them empty and reject attempts to use them.
- Analytical profile manages geographic context and analytics topic scope. The server now requires analytics entitlement and enforces the plan's topic limit. Explicit `null` values can clear location/topic fields.
- Profile Intelligence is distinct from the older Portfolio Analytics dashboard.

## Perception audience semantics

- Conversation participants are unique commenters in the selected period.
- Audience country/region/professional breakdowns are derived from commenters, not likes/views/shares.
- A perception with zero comments therefore reports zero conversation participants and no audience breakdown, even if it has many views or likes.
- Semantic professional/geographic cohorts remain based on analyzed comments and the minimum sample of 5.

## Portfolio analytics scope

- `/api/analytics/overview` and `/api/analytics/intelligence` are scoped to the authenticated user's authored Perceptions and selected analytics topics.
- `/api/analytics/decision` inherits that scoped overview.
- This prevents a subscriber from receiving platform-wide portfolio data through a user-scoped analytics endpoint.

## Subscription entitlement

- `active` and `trialing` subscriptions are entitled while their current period has not expired.
- `past_due` is entitled only while a valid future period boundary remains. Missing/expired period boundaries fail closed.
- The same entitlement rule is used by subscription output, analytics access, and billing synchronization.
- Observer access to a Perception's conversation intelligence remains intentionally separate from creator/profile analytics; the observer receives conversation-level aggregates without creator-only measurements.

## Demo fixtures

`app.seed_demo` now includes deterministic fixtures for: zero-comment/high-engagement, rich multi-region conversations, a four-comment sample threshold, three longitudinal 30-day buckets, analyzed synthetic comment intelligence, replies, and subscription edge states. This allows frontend tests to exercise both available and suppressed intelligence without depending on the external LLM provider.
