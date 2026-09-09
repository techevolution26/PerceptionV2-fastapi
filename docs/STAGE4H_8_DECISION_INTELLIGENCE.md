# Stage 4H.8 — Decision Intelligence Foundation

## Purpose

Stage 4H.8 adds a deterministic decision-intelligence framing layer on top of the validated Perception Intelligence evidence pipeline.

The layer does **not** create new evidence. It reframes already-qualified observations for a selected decision intent.

## Decision intents

- research
- business
- policy
- journalism
- education
- product
- professional
- general_exploration

## Contract

`decision_context` now contains:

- `intent`
- `status`
- `summary`
- `observations[]`
- `considerations[]`
- `evidence_invariant`
- `guardrail`
- `limitations[]`

Each observation carries its source type and qualifying sample size.

## Invariants

1. Decision framing must not change measurements, sample sizes, periods, cohort definitions, or observed descriptions.
2. Decision framing is unavailable when there is no qualifying semantic evidence.
3. No individual participant identities are exposed.
4. No city-level reporting is introduced.
5. No causal, predictive, population-wide, or psychological claims are generated.
6. Different intents may change recommended investigative/use context, but the underlying observations remain identical.
7. The existing observer/author entitlement boundary remains unchanged.

## Examples of safe framing

- Research: observed themes become hypotheses or areas for further investigation.
- Business: observed concerns become areas for market/customer follow-up, not demand estimates.
- Policy: observed concerns become consultation/investigation areas, not public-opinion estimates.
- Journalism: recurring themes become reporting leads that require independent verification.
- Education: questions and themes become candidate areas for explanation or learning support.
- Product: concerns and questions become discovery candidates, not automatic requirements.
- Professional: cross-lens differences become areas for reflection or inquiry.
- General exploration: patterns become structured starting points for further investigation.

## API

The existing endpoint remains:

`GET /api/analytics/perceptions/{perception_id}`

with the existing optional query parameter:

`decision_intent=<intent>`

No database migration is required.
