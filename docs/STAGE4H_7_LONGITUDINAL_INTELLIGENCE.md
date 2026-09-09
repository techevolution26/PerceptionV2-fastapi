# Stage 4H.7 — Longitudinal Intelligence

## Purpose

Move from intelligence about one Perception to longitudinal intelligence across the current user's authored Perceptions and Topics over time.

This is the bridge from **Perception Intelligence → Profile Intelligence**.

## Contract

- Scope is limited to the authenticated user's authored Perceptions.
- Topic and Professional Identity remain orthogonal.
- Professional identity does not imply authority over a Topic.
- Evidence is stored comment intelligence; derived patterns are not evidence themselves.
- Minimum analytical sample remains **5**.
- No individual participant identities are exposed.
- No sensitive-trait inference, causal claims, or predictive claims.
- Time is represented using 30-day buckets.
- The default longitudinal window is 180 days; callers may request 30–365 days.
- Only qualifying buckets and Topics are surfaced when the minimum sample is met.

## Endpoint

`GET /api/analytics/profile?days=180`

The endpoint requires the user's analytics-enabled access and returns `ProfileIntelligence`.

## Layers

1. **Portfolio** — authored Perception count, Topic count, analyzed response count, qualifying Perception count.
2. **Topic** — aggregate semantic evidence for Topics with at least 5 analyzed comments.
3. **Recurring themes** — themes observed across at least two Topics and at least 5 analyzed comments.
4. **Temporal** — qualifying 30-day windows across the portfolio.
5. **Patterns** — deterministic observations such as recurring themes, multiple qualifying Topics, and observed leading-stance change between qualifying windows.

## Interpretation guardrails

Longitudinal intelligence describes observed recurrence and change in the platform dataset. It does not establish why a theme recurs, whether an observed change is durable, or whether the dataset represents a wider population.
