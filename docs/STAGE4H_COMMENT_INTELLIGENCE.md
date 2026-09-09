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

## Professional × geographic semantic cross-analysis

The next intelligence layer compares stored semantic signals across aggregate
participant cohorts. It does not run another model and does not expose people.

- Professional cohorts use the participant's primary structured professional role.
- Geographic cohorts use country and country-region; city is never exposed.
- Professional + geographic cohorts combine those two dimensions.
- Every cohort is independently suppressed unless it contains at least 5 analyzed comments.
- Reported fields include sample size, sentiment distribution, stance distribution, top themes, question count, and mean analysis quality where available.
- No causal, population-representative, or individual-level inference is made.
- A comment is attributed to its comment author's cohort; raw participant identities are never returned by the analytics API.
