# Stage 4H — Comment Intelligence Foundation

## Purpose

Stage 4H establishes the distinction between creator analytics and public conversation intelligence for the Perception analytics surface.

## Viewer model

- **Author** → `viewer_lens=author`, `intelligence_scope=creator_analytics`.
  - Requires an analytics-enabled plan.
  - Receives performance and audience aggregates for their own Perception.
- **Non-author** → `viewer_lens=observer`, `intelligence_scope=conversation_intelligence`.
  - Does not require the author's analytics subscription.
  - Receives aggregate conversation signals only.
  - Never receives private creator analytics.

## Privacy guardrails

- Participant identity is never returned from the Perception intelligence endpoint.
- Professional and geographic breakdowns require at least 5 unique interacting participants.
- City-level reporting is not exposed.
- Verified professional-role aggregates use only platform-confirmed roles.
- Small samples are suppressed rather than inferred.

## Semantic intelligence contract

The response now explicitly exposes `semantic_analysis_status` and `semantic_analysis_note`. Stage 4H does **not** invent sentiment, stance, themes, or other AI-generated interpretations before the semantic analysis layer exists.

The next implementation can add comment-level semantic processing behind this contract:

- sentiment
- stance
- semantic themes
- questions / concerns
- areas of agreement
- areas of disagreement

Every interpretation should retain evidence metadata such as sample size, analysis period, confidence/quality indicators, and suppression state.

## Comment-analysis data model

`comment_intelligence` stores one normalized semantic result per comment. It is
provider-neutral and contains:

- analysis status (`pending`, `analyzed`, `failed`)
- sentiment (`positive`, `negative`, `neutral`, `mixed`, `unclear`)
- stance (`supportive`, `challenging`, `mixed`, `unclear`)
- up to 10 semantic themes
- question/concern/agreement/disagreement signals
- quality score, model version, analysis timestamp and optional error code

No raw prompts, provider payloads, or participant identity are stored in this
semantic result table.

## Aggregation contract

The Perception analytics endpoint aggregates only rows with `status=analyzed`
and applies a minimum sample of 5 analyzed comments. Below that threshold the
semantic layer is explicitly `insufficient_sample` and distributions are empty.
When available, the response includes sentiment and stance distributions, top
themes, question count, agreement/concern/disagreement themes, analyzed sample
size, analysis period and an average analysis-quality score.

The aggregate is evidence metadata, not statistical confidence and not causal
inference. A future worker may write results through the normalized service
contract without changing the public analytics response shape.

## Semantic analysis engine

The semantic layer now has an opt-in provider adapter and background worker.
The current adapter uses the OpenAI Responses API with strict JSON Schema output.
The worker sends only the perception text, topic name, and comment text needed
for semantic classification; it does not send commenter identity or profile
attributes. Provider responses are not persisted.

Configuration:

- `COMMENT_INTELLIGENCE_ENABLED=false` by default, to prevent accidental model spend.
- `COMMENT_INTELLIGENCE_MODEL=gpt-5.6-luna` for the cost-sensitive high-volume path.
- `COMMENT_INTELLIGENCE_BATCH_SIZE=10` comments per scheduled pass.
- `COMMENT_INTELLIGENCE_INTERVAL_SECONDS=60` between passes.
- `OPENAI_API_KEY` is required when the engine is enabled in production.
- `OPENAI_BASE_URL` defaults to the OpenAI API and remains configurable for a compatible provider.

New comments and replies are queued as `pending`. The scheduler processes a
bounded batch and writes only the normalized `comment_intelligence` fields.
Transient provider failures remain retryable; invalid or unsupported results are
recorded as a safe failure code without storing raw provider output.

The worker also backfills comments that predate Stage 4H by creating their
normalized `pending` record on the next scheduled pass. This avoids requiring a
new database migration just to enqueue historical comments.
