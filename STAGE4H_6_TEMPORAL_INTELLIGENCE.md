# Stage 4H.6 — Temporal Intelligence

Temporal intelligence adds deterministic time-window analysis to Perception Intelligence.

## Contract

- Seven-day response windows are used within the selected analytics period.
- A window is analytically available only when it contains at least 5 analyzed comments.
- Windows below the threshold remain visible only as suppressed sample windows; their semantic fields are empty.
- Trends compare qualifying windows only. Missing/suppressed windows are never interpolated or treated as zero.
- The original `Comment.created_at` is used for temporal placement, not the analysis record timestamp.
- No participant identities are exposed.
- Temporal association does not establish causation or population-wide change.

## Output

`PerceptionIntelligence.temporal` contains:

- `status`
- `bucket_days`
- `sample_minimum`
- `qualifying_bucket_count`
- `buckets`
- `changes`
- `note`
- `limitations`

Each qualifying bucket carries sentiment and stance distributions, top themes, question count, sample size, and quality score.

Each change records whether the leading stance and leading theme changed between adjacent qualifying windows.
