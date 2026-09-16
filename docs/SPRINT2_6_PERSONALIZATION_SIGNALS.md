# Sprint 2.6 — Personalization Signals

## Objective
Connect the user's existing context and explicit behavior to feed relevance without turning personalization into popularity ranking.

## Signals
- Followed Topics: strong relevance signal.
- Followed creators: strong relevance signal.
- Explicit interaction topics: likes, saves, and comments create topic-interest signals.
- Professional identity: primary role and mother industry can increase contextual relevance.
- Geographic context: country/region can contribute only when the creator has explicitly made that broad location public. City is never used in the public-facing result.
- Recency: a bounded freshness signal prevents the feed from becoming a static topic archive.

## Explicitly excluded from personalization score
- Global likes count.
- Global comments count.
- Global views count.
- Follower count.
- Engagement-rate ranking.
- Participant identity from intelligence aggregates.
- Precise device location.

## API
`GET /api/perceptions/personalized`

Authenticated only. Returns the existing `PerceptionOut` contract, so action synchronization and existing card behavior remain unchanged.

The endpoint ranks a bounded recent candidate pool and performs no LLM/provider call in the request path.

## Product behavior
Authenticated Home uses the personalized endpoint. Guests continue using the public chronological feed.

The recommendation is a relevance layer, not an intelligence layer. Topic Intelligence, Perception Intelligence, and decision contracts remain separate.
