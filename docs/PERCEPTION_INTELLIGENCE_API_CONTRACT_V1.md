# Perception Intelligence API Contract v1

## Endpoint

`GET /api/analytics/perceptions/{perception_id}`

Query parameters:

- `days`: selected observation window, clamped to 7–365 days.
- `decision_intent`: optional framing intent: `research`, `business`, `policy`, `journalism`, `education`, `product`, `professional`, or `general_exploration`.

## Contract shape

The endpoint returns one stable `PerceptionIntelligence` document. The API no longer exposes the perception report as a flat `PerceptionAnalyticsOut` object.

```text
PerceptionIntelligence
├── context
│   ├── schema_version
│   ├── topic
│   ├── perception_id
│   ├── period
│   ├── scope
│   ├── viewer_lens
│   └── author
├── measurements
├── audience
├── semantic
├── perspectives
│   ├── professional
│   ├── geographic
│   └── cross_lens
├── patterns
├── signals
├── decision_context
└── methodology
```

## Contract rules

1. Topic is first-class context. A perception is always interpreted under its topic.
2. `viewer_lens` separates author `creator_analytics` from observer `conversation_intelligence`.
3. Creator-only measurements (`views`, `shares`, `engagement_rate`, and daily activity) are unavailable to observers.
4. Audience breakdowns require at least 5 unique interacting participants.
5. Semantic intelligence requires at least 5 analyzed comments.
6. Professional, geographic, and professional×geographic semantic cohorts independently require at least 5 analyzed comments.
7. Geographic reporting uses country and region; city-level reporting is not exposed.
8. Individual participant identities are never returned by the intelligence contract.
9. `patterns` and `signals` contain only deterministic, evidence-backed descriptive observations. They remain empty below the semantic sample minimum.
10. `decision_context` changes framing intent only. It is evidence-invariant and does not establish causation or prediction.
11. `methodology` travels with the result so consumers do not need to reconstruct analytical limitations separately.
12. `schema_version` allows future contract evolution without silently changing the meaning of an existing response.
13. Pattern and signal descriptions must remain scoped to the observed evidence and must not introduce causal or predictive claims.

## Semantic meanings

- Sentiment describes the feeling expressed toward the discussion.
- Stance describes the relationship to the proposition (`supportive`, `challenging`, `mixed`, `unclear`).
- Themes are aggregate semantic labels from analyzed comments.
- Questions, concerns, agreement, and disagreement are aggregate signals; they do not expose comment text or participant identity.

## Frontend rule

The mobile Perception Intelligence screen consumes this structured contract directly. New intelligence layers should be added inside the contract rather than appended to a flat analytics object.
