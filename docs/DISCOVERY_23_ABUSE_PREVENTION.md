# Discovery 23 — Abuse Prevention

## Objective
Protect conversations from high-volume automated or repetitive behavior without profiling people or turning normal disagreement into a moderation signal.

## Controls
- Per-authenticated-user rate limits are enforced for perception creation, comment/reply creation, and reports.
- Redis stores only a one-way identity digest plus a short-lived counter; raw user identifiers are not used as Redis keys.
- Perception creation: 6 requests/minute by default.
- Comment/reply creation: 20 requests/minute by default.
- Reports: 5 requests/10 minutes by default.
- Redis failure fails closed unless the existing `RATE_LIMIT_FAIL_OPEN` development setting is explicitly enabled; production validation prohibits fail-open mode.
- HTTP 429 responses include `Retry-After`.
- Existing per-user/perception report uniqueness remains authoritative, so rate limiting does not replace database integrity.

## Deliberate exclusions
- No IP-based long-term profiling.
- No device fingerprinting.
- No location tracking.
- No scoring of viewpoints or political/ideological content.
- No follower/engagement-based suspicion score.
- No LLM in the request path.
- No automated account suspension from a single threshold breach.

## Product principle
Rate limits slow abusive throughput; they do not decide whether a person's perspective belongs in the conversation.
