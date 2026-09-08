# Stage 4H — Comment Intelligence Rate-Limit Hardening

This stage hardens the comment-intelligence provider against upstream HTTP 429 responses.

## Behavior

- Reads `Retry-After` from provider 429 responses.
- When request capacity is exhausted (`x-ratelimit-remaining-requests: 0`), also reads `x-ratelimit-reset-requests` and uses the longer safe cooldown.
- Persists the provider cooldown in Redis so scheduler runs do not immediately retry after a container restart.
- Caps the cooldown at `COMMENT_INTELLIGENCE_COOLDOWN_MAX_SECONDS` (default 24 hours).
- A 429 remains retryable and leaves comments in `pending` state.
- The current worker batch stops after the first 429 instead of issuing one request per pending comment.
- Subsequent scheduler cycles return without calling the provider while the cooldown is active.
- 5xx responses remain retryable; 401/403 are treated as authentication/authorization failures.

## Current observed provider state

The provider previously returned 429 with request capacity exhausted. The implementation now respects those upstream signals instead of retrying every 60 seconds.
