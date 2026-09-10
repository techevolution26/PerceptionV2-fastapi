# Stage 4H.13 — AI Quality & Governance

## Purpose

Make AI-derived semantic intelligence auditable at the aggregate level without
exposing provider payloads, prompts, participant identities, or hidden model
reasoning.

## Quality contract

Each perception intelligence response now includes a `quality` section covering:

- analyzed comment count;
- aggregate analysis quality score;
- low-quality analysis count/share;
- pending and failed analysis counts;
- model-version coverage;
- explicit limitations.

Quality is available only after the existing minimum sample of 5 analyzed
comments. Below that threshold, quality interpretation is withheld.

## Interpretation

The stored `quality_score` is a model-output quality indicator. It is not
statistical confidence, population representativeness, factual truth, or a
measure of the quality of the underlying comments.

Scores below 0.60 are classified as low-quality analysis for operational
monitoring. They remain retained for auditability but are not promoted as
stronger evidence.

## Safety boundaries

- No participant identity is exposed.
- No raw provider response or prompt is stored.
- No sensitive trait inference is added.
- No causal or predictive claim is generated.
- Model version is reported only as aggregate coverage metadata.
- Quality metadata does not override minimum-sample or freshness gates.

## Operational use

This layer separates three questions:

1. **Is there enough evidence?** — sample/freshness rules.
2. **Is the semantic processing healthy enough to interpret?** — quality rules.
3. **What does the evidence show?** — patterns, signals, perspectives, and
   decision framing.

The system must not collapse these into a single confidence number.
