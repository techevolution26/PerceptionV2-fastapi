# Stage 4H.9 — Intelligence Acceptance & Regression Gate

Stage 4H.9 is a stabilization stage. It does not introduce a new analytical capability.
It establishes deterministic contract invariants around the 4H.7–4H.8 intelligence stack.

## Invariants

- Observer scope cannot expose creator-only views, shares, engagement rate, or daily activity.
- Conversation participants are comment-derived.
- Audience breakdowns require the minimum sample.
- Semantic distributions are unavailable below the analyzed-comment minimum.
- Semantic distribution counts use the `comments` field consistently.
- Decision framing must preserve `evidence_invariant=true`.
- The guard is provider-independent and does not create or alter evidence.

## Acceptance fixtures

The seeded scenarios remain the primary runtime acceptance fixtures:

1. zero-comment / high-interaction perception;
2. four-comment threshold perception;
3. rich multi-region / multi-profession conversation;
4. longitudinal multi-bucket conversation;
5. subscription entitlement edge cases.

4H.9 should be considered complete only after the seeded API responses and the pure contract guard tests agree with these rules.
