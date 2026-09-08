# Stage 4H — Unified Perception Analytics & Intelligence

## Interaction model

A Perception has one analytics/intelligence surface with two entry points:

- Analytics icon: quick access to the selected Perception's report.
- More → Perception Intelligence: deliberate access to the same selected Perception report.

The destination is always `/perceptions/{id}/analytics`.

## Viewer lenses

- Author → `creator_analytics`: private performance and audience analytics.
- Non-author → `conversation_intelligence`: aggregate conversation signals only.

Observer responses intentionally omit creator-performance metrics such as views,
shares, engagement rate, and daily activity. Public engagement counts such as
likes/comments may remain visible, while participant identity is never exposed.

## Semantic intelligence

Semantic signals come only from stored analyzed-comment results and remain
suppressed until the minimum analyzed-comment sample is reached. No AI provider
or LLM is invoked by this stage.
