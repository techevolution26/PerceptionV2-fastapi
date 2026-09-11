# Stage 5.1.1 — Topic Evidence Scope & Participant Privacy

## Purpose

Define exactly which stored evidence is allowed to contribute to Topic Intelligence and when Topic-level semantic conclusions may be released.

## Scope rules

1. Only active Perceptions belonging to the requested Topic are eligible.
2. Only responses whose `CommentIntelligence.status == analyzed` are eligible.
3. Pending and failed semantic analyses are excluded.
4. The requested time window is bounded to 30–365 days.
5. Topic breadth requires at least 2 Perceptions that independently contain at least 5 analyzed comments.
6. Topic-wide semantic conclusions additionally require at least 5 unique active participants.
7. Unique participant counts below 5 are suppressed rather than returned.
8. Professional, geographic, and professional×geographic cohorts require both the comment minimum and the unique-participant minimum when used by Topic Intelligence.
9. No participant identity is returned.
10. City-level aggregation is never returned.
11. The topic endpoint is authenticated; frontend visibility is not a security boundary.
12. No provider/LLM call is made during the request.

## Privacy rationale

A five-comment threshold alone is insufficient as a privacy boundary because one participant could create all five comments. Topic Intelligence therefore separates:

- **observation minimum:** 5 analyzed comments;
- **breadth minimum:** 2 qualifying Perceptions;
- **participant privacy minimum:** 5 unique participants.

All three conditions must qualify before Topic-wide semantic conclusions are released.

## Suppression behavior

When the participant privacy minimum is not met:

- semantic distributions are withheld;
- Topic patterns are withheld;
- unique participant count is suppressed;
- professional/geographic Topic perspectives are withheld;
- no participant identity is exposed;
- the API reports an explicit insufficient-participants status.

## Evidence invariant

Decision intent changes framing only. It cannot change the selected evidence, sample, time period, cohort qualification, or privacy thresholds.

## Non-goals

This slice does not add:

- new persisted intelligence entities;
- new AI providers;
- participant profiling;
- city intelligence;
- causal inference;
- predictive claims;
- population estimates;
- new frontend surfaces.

The next implementation slice may consume this scope contract without changing the frozen 4H core.
