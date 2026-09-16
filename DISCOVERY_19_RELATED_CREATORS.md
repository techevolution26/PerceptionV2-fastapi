# Discovery 19 — Related Creators

## Objective

Surface creators who are contextually relevant to the Topic being viewed, using the same perception graph and trust boundaries established by Discovery 17–18.

## Endpoint

`GET /api/topics/{topic_id}/related-creators`

Optional authentication personalizes the result. Guests receive context-only results.

## Signals

- Active creators currently contributing perceptions to the viewed Topic.
- Qualified conversation themes from analyzed comments: minimum 5 analyzed comments and 5 distinct participants before semantic themes can contribute.
- Professional perspective overlap through primary professional role.
- Explicit viewer affinity through followed creators, role, and industry.
- Public broad geography can add a small contextual signal only when the creator has explicitly exposed country/region visibility.
- Recent creator activity is a small recency tie-breaker.

## Ranking exclusions

- Follower count.
- Likes, comments, views, shares, or engagement rate.
- City or GPS location.
- Participant identity from intelligence aggregates.
- LLM/provider calls in the request path.
- Popularity-based creator ranking.

Creators already followed by the viewer and the viewer themselves are excluded from the recommendation set.

## Privacy

Creator identity is intentionally surfaced because the product is recommending a public creator. Semantic participant identities are never returned as part of the intelligence-derived relationship. Public location is limited to the existing country/region visibility contract; private location contributes no signal.

## Product placement

Topic detail displays a **Related creators** section alongside Related topics. Each result shows the existing professional identity/verification presentation and an explainable relationship reason, then navigates to the creator profile.

## Acceptance

- Existing topic/perception APIs remain unchanged.
- No migration required.
- Backend compile passes.
- Runtime pytest remains environment-blocked where `asyncpg` is unavailable.
- Mobile TypeScript requires the project's installed dependencies and should be run locally before release acceptance.
