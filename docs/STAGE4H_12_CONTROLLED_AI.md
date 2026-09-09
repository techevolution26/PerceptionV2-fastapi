# Stage 4H.12 — Controlled AI Semantic Processing

## Purpose

Activate the existing `CommentIntelligence` queue as a bounded, background-only semantic processing pipeline. The AI provider is an implementation detail behind the existing evidence contract; the public analytics response shape does not change.

## Controls

- Disabled by default with `COMMENT_INTELLIGENCE_ENABLED=false`.
- No provider call occurs in an API request path.
- Processing is bounded by `COMMENT_INTELLIGENCE_BATCH_SIZE`.
- A Redis distributed lock prevents duplicate workers across API replicas.
- Provider cooldown is persisted in Redis so a restart does not immediately retry a rate-limited provider.
- HTTP 429 pauses processing immediately; `Retry-After` is preferred and `x-ratelimit-reset-requests` is a fallback.
- Cooldown is bounded by `COMMENT_INTELLIGENCE_MAX_COOLDOWN_SECONDS` (default 24 hours).
- Transient timeouts/request failures/server errors leave comments pending for later retry.
- Authentication/configuration and invalid provider output become safe failed states.
- The provider request uses `store=false` and strict JSON schema output.
- Only normalized semantic fields are stored; raw provider payloads and prompts are not stored.

## Semantic boundary

The model may classify only the supplied perception topic/body and comment. It must not infer commenter identity, protected traits, profession, location, health, religion, ethnicity, gender, politics, or other sensitive attributes.

The resulting fields are evidence annotations, not participant profiles, causal claims, statistical confidence, or predictions.

## Freshness behavior

New comments remain `pending` until processed. The analytics API reports freshness and does not silently invoke the provider. Existing aggregate minimum-sample and privacy rules remain authoritative.

## Operational configuration

- `COMMENT_INTELLIGENCE_ENABLED=false`
- `COMMENT_INTELLIGENCE_MODEL=gpt-5.6-luna`
- `COMMENT_INTELLIGENCE_BATCH_SIZE=10`
- `COMMENT_INTELLIGENCE_INTERVAL_SECONDS=60`
- `COMMENT_INTELLIGENCE_DEFAULT_COOLDOWN_SECONDS=60`
- `COMMENT_INTELLIGENCE_MAX_COOLDOWN_SECONDS=86400`
- `OPENAI_API_KEY=`
- `OPENAI_BASE_URL=https://api.openai.com/v1`

The worker is designed to sleep while a provider cooldown is active and resume only after the persisted cooldown expires.
