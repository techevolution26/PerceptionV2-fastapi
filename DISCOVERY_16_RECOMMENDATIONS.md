# Discovery 16 — Recommendations

## Objective
Provide explainable recommendations for topics, creators, and perceptions using the existing personalization signals without turning recommendations into popularity ranking.

## Contract
- Authenticated users only.
- `GET /api/recommendations` returns three bounded collections: topics, creators, perceptions.
- Every item includes a human-readable `reason`.
- Recommendation score is an internal relevance ordering value and is not exposed as a user-facing rating.
- No likes, comments, views, followers, or engagement rate are used as recommendation signals.
- Public geography can contribute only at country/region scope; city and precise location never contribute.
- Followed topics, followed creators, and the current user are excluded from the corresponding discovery recommendations.
- No LLM/provider call is made in the request path.

## Relationship to feed ranking
Feed ranking answers what should appear in the feed. Recommendations answer what new topic, creator, or perception a user may want to explore and explain why it was suggested.

## Privacy
Recommendations use the same `PersonalizationProfile` and public geography boundaries as Discovery 15. No participant identity is inferred from intelligence aggregates.
