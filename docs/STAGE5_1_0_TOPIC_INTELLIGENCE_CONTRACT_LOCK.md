# Stage 5.1.0 — Topic Intelligence Contract Lock

## Status

Contract lock only. No application behavior, database migration, provider, or frontend implementation is introduced by this stage.

## Purpose

Topic Intelligence is the first higher-level intelligence capability built on the frozen Core Intelligence Foundation. It expands analytical scope from one Perception to a qualified set of Perceptions that belong to one Topic.

It does **not** create a second semantic engine. It consumes the existing `CommentIntelligence`, evidence, provenance, quality, freshness, model-governance, cross-lens, temporal, and decision-intelligence contracts.

## Core model

```text
Topic
  └── Perception(s)
        └── Response / Comment(s)
              └── CommentIntelligence
                    ├── sentiment
                    ├── stance
                    ├── themes
                    ├── questions / concerns
                    ├── agreement / disagreement
                    ├── quality
                    ├── model version
                    └── analysis timestamp
```

Topic Intelligence derives higher-level evidence from those existing records.

## Fundamental invariants

1. **Topic is first-class.**
2. **Topic and professional identity are orthogonal.**
3. **Human responses remain the evidence.**
4. **AI interpretation is derived analysis, not evidence.**
5. **Differences between legitimate lenses are analytical data.**
6. **The frozen Core Intelligence contracts are not modified.**
7. **No new LLM request is made merely to summarize a Topic.**
8. **AI is never a request-path dependency.**
9. **No participant identity is exposed through Topic Intelligence.**
10. **City-level aggregate intelligence is excluded.**
11. **No sensitive-trait inference, causal claim, clinical claim, predictive claim, or population estimate is produced.**
12. **Backend authorization and entitlement are authoritative; frontend visibility is never security.**
13. **Decision framing cannot alter the underlying evidence.**

## Qualification model

Topic Intelligence has two independent qualification dimensions.

### Response qualification

Only stored `CommentIntelligence` rows with:

- `status = analyzed`
- valid evidence timestamps
- valid quality/governance state

are eligible for Topic-level semantic analysis.

Pending and failed analyses are excluded from analytical evidence.

### Perception qualification

A Perception qualifies for Topic-wide breadth only when it independently contains at least **5 analyzed responses** in the selected period.

Topic-wide semantic conclusions require at least **2 qualifying Perceptions**.

This prevents a single highly active Perception from being silently represented as the voice of an entire Topic.

A Topic with 10 analyzed comments in one Perception and no second qualifying Perception therefore does **not** qualify for Topic-wide conclusions.

## Topic scope

The initial Topic Intelligence scope is:

```text
one Topic
→ active Perceptions belonging to that Topic
→ responses within the requested time period
→ analyzed CommentIntelligence evidence
```

Inactive users and inactive content must not contribute to the analytical scope.

Topic membership is taken from the persisted `Perception.topic_id`; the system must not infer Topic membership from free-text content.

## Time

The API will use a bounded period, with the first implementation expected to support:

- default: 180 days
- minimum: 30 days
- maximum: 365 days

Temporal placement uses the original response/comment timestamp.

No suppressed temporal window is interpolated or converted into a zero-observation period.

## Contract shape

The first public contract is intentionally nested and evidence-oriented:

```text
TopicIntelligence
├── schema_version
├── context
│   ├── topic_id
│   ├── topic_name
│   ├── period
│   ├── scope
│   ├── viewer_lens
│   └── access tier
├── measurements
├── perceptions
├── semantic
├── perspectives
│   ├── professional
│   ├── geographic
│   └── professional_geographic
├── temporal
├── patterns
├── decision_context
├── provenance
└── limitations
```

The contract may gain additional governed fields in later slices, but existing Core Intelligence contracts must remain compatible.

## Measurements

Topic measurements may include:

- active Perception count in scope
- qualifying Perception count
- analyzed response count
- unique participant count where the existing privacy rules permit its aggregate display

Participant identity must never be serialized as part of this contract.

## Semantic layer

When qualified, Topic semantic evidence may include:

- sentiment distribution
- stance distribution
- recurring themes
- question activity
- concern themes
- agreement signals/themes
- disagreement signals/themes
- aggregate quality

Sentiment means the observed feeling toward the discussion.

Stance means the observed relationship to the proposition.

No semantic result should be presented as proof of causation or population-wide opinion.

## Perspectives

Topic Intelligence may expose aggregate perspectives by legitimate contextual lenses:

- professional role
- country/region geography
- professional role × geography

Every cohort independently requires the existing minimum analytical sample of **5**.

Professional identity is contextual and does not automatically imply authority or expertise on the Topic.

City-level cohorts are not exposed.

## Patterns

Patterns are deterministic derived observations from qualifying Topic evidence.

Examples may include:

- dominant observed sentiment
- dominant observed stance
- recurring themes
- question activity
- concern activity
- agreement/disagreement activity
- qualifying perspective differences

Patterns must retain their evidence basis and limitations.

## Signals

Signals are higher-level qualified observations built from patterns and governed evidence.

Signals are not predictions and are not causal explanations.

A signal must not be emitted when its underlying evidence fails the applicable sample, quality, freshness, or governance requirements.

## Convergence and divergence

Where multiple qualifying lenses exist, Topic Intelligence may identify:

- convergence: meaningful similarity across qualifying cohorts
- divergence: meaningful difference across qualifying cohorts

The system should report the observed difference rather than inventing a reason for that difference.

For example, a professional or geographic cohort may show a different leading stance or theme. Topic Intelligence must not claim that profession or geography caused that difference.

## Temporal intelligence

Topic temporal intelligence reuses the existing temporal principles:

- fixed bounded windows
- minimum 5 analyzed responses per qualifying window
- original comment timestamps
- no interpolation
- no zero-filling of suppressed windows
- changes only between qualifying windows

## Decision context

Supported decision intents remain:

- research
- business
- policy
- journalism
- education
- product
- professional
- general exploration

Changing the decision intent changes framing only.

It must not change:

- source responses
- sample sizes
- cohort definitions
- periods
- observed distributions
- evidence qualification

The response must preserve an explicit evidence invariant.

## Provenance

Every meaningful Topic Intelligence result must remain traceable through the existing evidence chain:

```text
Human response
    ↓
CommentIntelligence
    ↓
Evidence
    ↓
Topic aggregation
    ↓
Pattern / signal / decision context
```

Provenance must retain, as applicable:

- trace ID
- evidence types
- sample size
- period
- scope
- viewer lens
- quality
- qualification
- limitations

## Quality

Existing quality governance remains authoritative.

The established low-quality threshold of `0.60` remains relevant to evidence qualification.

Topic aggregation must not use failed/pending semantic rows as if they were analyzed evidence.

## Freshness

Existing freshness governance remains authoritative.

Topic Intelligence must report or respect whether its underlying evidence is current, pending, or stale.

Stale evidence must not silently appear as current intelligence.

## Model governance

Existing semantic model governance remains authoritative.

Topic Intelligence must retain model-version context where it materially affects evidence interpretation.

A model change must not silently create an apparently comparable Topic trend when governance indicates review is required.

## Access model

Topic Intelligence is an authenticated capability.

The contract supports the existing capability-tier model:

```text
free_teaser
full
```

The exact commercial plan, price, billing interval, and future entitlement limits are **not locked by this contract**.

Backend entitlement remains authoritative.

Frontend code must render the access tier returned by the backend and must never calculate entitlement itself.

## Privacy release gate

Every Topic Intelligence request must conceptually pass:

```text
Authentication
      ↓
Authorization
      ↓
Entitlement
      ↓
Topic scope
      ↓
Active/qualifying Perceptions
      ↓
Qualifying responses
      ↓
Minimum response sample
      ↓
Minimum Perception breadth
      ↓
Data minimization
      ↓
No participant identity
      ↓
No sensitive inference
      ↓
No city aggregate
      ↓
Evidence / provenance
      ↓
Freshness
      ↓
Quality
      ↓
Model governance
      ↓
Response
```

This is a permanent release gate, not a frontend feature flag.

## API boundary

The preferred resource hierarchy is:

```text
/api/topics
/api/topics/{id}
/api/topics/{id}/perceptions
/api/topics/{id}/follow
/api/topics/{id}/intelligence
```

The preferred Topic Intelligence endpoint is therefore:

`GET /api/topics/{topic_id}/intelligence`

This keeps Topic Intelligence under the Topic resource rather than treating it as an unrelated global analytics object.

Supported query inputs are expected to include:

- `days`
- `decision_intent`

The final response schema must be validated by Pydantic before release.

## Frontend contract

The Topic detail surface remains the entry point.

Existing flow:

```text
Topics
  ↓
Topic detail
  ↓
Perceptions under Topic
```

New flow:

```text
Topics
  ↓
Topic detail
  ↓
View Topic Intelligence
  ↓
Topic Intelligence screen
```

Expected native route:

`/topics/[id]/intelligence`

The web application should expose the same conceptual surface using its existing routing conventions.

The frontend may:

- request the endpoint
- display loading/error/empty states
- render backend-provided measurements
- render semantic distributions
- render patterns/signals
- render perspectives
- render temporal information
- render decision context
- render provenance/limitations
- show upgrade UI when the backend returns an upgrade state

The frontend must **not** calculate:

- sample qualification
- privacy qualification
- cohort eligibility
- pattern qualification
- signal qualification
- evidence status
- freshness status
- quality status
- authorization
- entitlement

## No new persistence yet

Stage 5.1 initially computes Topic Intelligence from existing persisted domain data.

No new `topic_intelligence`, `topic_patterns`, or `topic_signals` tables are introduced at contract-lock stage.

Persistence can be reconsidered later only if there is demonstrated need for:

- historical snapshots
- expensive computation
- audit workflows
- reusable intelligence artifacts
- explicit analytical versioning

## Non-goals

Stage 5.1 does not introduce:

- a second AI/semantic engine
- participant profiling
- identity-level analytics
- city-level intelligence
- sensitive-trait inference
- causal inference
- clinical conclusions
- predictive claims
- population estimates
- organizational intelligence
- automatic professional authority
- a new frontend state architecture
- a new API client
- a new AI provider

## Planned implementation slices

```text
5.1.0  Topic Intelligence Contract Lock       ← THIS STAGE
        ↓
5.1.1  Topic Evidence Scope
        ↓
5.1.2  Topic Semantic Aggregation
        ↓
5.1.3  Topic Patterns & Signals
        ↓
5.1.4  Topic Convergence / Divergence
        ↓
5.1.5  Topic Professional / Geographic Perspectives
        ↓
5.1.6  Topic Temporal Intelligence
        ↓
5.1.7  Topic Decision Context
        ↓
5.1.8  Privacy / Authorization Gate
        ↓
5.1.9  Backend Acceptance Tests
        ↓
5.1.10 Web + Native Surfaces
```

Each slice must preserve the frozen Core Intelligence Foundation.

## Acceptance criteria for this contract lock

- Topic is explicitly first-class.
- Topic Intelligence is scoped to a Topic, not globally inferred from arbitrary text.
- Response qualification and Perception qualification are separate.
- Minimum response sample is 5.
- Minimum Topic breadth is 2 qualifying Perceptions.
- Pending/failed analyses are excluded.
- Participant identities are excluded.
- City-level aggregate intelligence is excluded.
- Professional identity remains contextual.
- Decision intent cannot change evidence.
- Existing provenance, quality, freshness, and model-governance rules remain authoritative.
- No new database tables are required.
- No new LLM request path is introduced.
- Backend authorization/entitlement remains authoritative.
- Web and native clients consume the same backend contract.
