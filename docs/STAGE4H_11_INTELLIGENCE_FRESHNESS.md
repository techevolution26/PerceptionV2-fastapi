# Stage 4H.11 — Intelligence Freshness & Recalculation

## Purpose

Make the relationship between source conversation changes and stored semantic intelligence explicit.

## Freshness states

- `current`: all comments in the selected period have analyzed intelligence and stored analysis is at least as recent as the latest source comment.
- `pending`: new comments are queued for analysis or source comments have no intelligence row yet.
- `stale`: stored intelligence is no longer aligned with the current conversation, including failed analysis requiring retry.

## Recalculation contract

Creating a comment or reply creates a `CommentIntelligence` row with `pending` status before the transaction commits. The analysis worker consumes pending rows. The analytics API reports whether recalculation is required; it does not silently invent or refresh semantic conclusions during a reader request.

No new database migration is required because the existing `CommentIntelligence` lifecycle fields already provide the queue and timestamps.

## Frontend analytics color language

- Green: current/strong or positive evidence.
- Amber: early/watch state, mixed evidence, or qualification requiring attention.
- Red: stale/caution or negative/challenging signal.
- Neutral: contextual information that should not be interpreted as a strength signal.

Colors are supplementary; labels and sample sizes remain authoritative for accessibility and meaning.
