# Stage 5.1 — Topic Intelligence Foundation

## Purpose

Topic Intelligence is the first higher-level intelligence surface after the Stage 4H production freeze. It aggregates evidence across multiple active Perceptions belonging to one Topic without changing the underlying evidence model.

## Contract

- Topic is first-class.
- Human responses remain the evidence source.
- Stored CommentIntelligence is a derived semantic layer.
- Minimum analyzed sample is 5 comments.
- Topic-level analytical breadth requires at least 2 qualifying Perceptions, each with at least 5 analyzed comments.
- Pending and failed analyses are excluded.
- Individual participant identities are never exposed.
- City-level aggregate intelligence is not exposed.
- Professional identity remains a contextual lens, not automatic authority.
- Topic and professional identity remain orthogonal.
- Temporal windows use actual comment timestamps and are not interpolated.
- Decision context cannot change the underlying evidence.
- No LLM/provider call occurs in the request path.

## Endpoint

`GET /api/analytics/topics/{topic_id}`

Query parameters:

- `days`: 30–365, default 180
- `decision_intent`: research, business, policy, journalism, education, product, professional, general_exploration

## Access

Authenticated users receive Topic Intelligence with the same capability-tier principle established in Stage 4H:

- `free_teaser`: bounded strongest observation only
- `full`: semantic, professional/geographic perspectives, temporal evidence, patterns and decision context

The topic aggregation itself is never personalized to the viewer's identity or professional status.

## Breadth rule

A Topic must have at least two Perceptions that independently meet the five-comment analytical threshold before Topic-wide semantic conclusions qualify.

This prevents a single highly active Perception from being silently presented as the voice of an entire Topic.

## Non-goals

Stage 5.1 does not introduce:

- new AI providers
- participant profiling
- city-level intelligence
- causal inference
- predictive claims
- population estimates
- organizational intelligence
- new persisted intelligence entities

Those can only be considered in later stages if they consume the frozen evidence, provenance, governance, privacy, and entitlement contracts.
