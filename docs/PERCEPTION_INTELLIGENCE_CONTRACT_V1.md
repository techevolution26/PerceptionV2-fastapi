# Perception Intelligence / Decision Intelligence Contract v1

Status: **LOCKED — Stage 4H Contract**

This document defines the product/domain contract before further intelligence implementation. It is intentionally separate from implementation details and payment configuration.

## 1. Core definition

A **Perception** is a proposition, observation, question, experience, or situation expressed **under a Topic**.

The canonical analytical unit is:

> **Topic × Perception × Lens × Response**

Topic gives the perception its domain meaning. A lens supplies legitimate contextual information about how a response is being interpreted. The response remains the underlying evidence.

## 2. Canonical intelligence pipeline

```text
Topic
  ↓
Perception
  ↓
Response
  ↓
Lens
  ↓
Evidence
  ↓
Semantic Interpretation
  ↓
Cross-Lens Pattern
  ↓
Signal
  ↓
Potential Implication
  ↓
Decision Context
```

The pipeline is ordered. Descriptive evidence precedes semantic interpretation; semantic interpretation precedes cross-lens comparison; signals precede potential implications.

## 3. Topic is first-class

A Perception is analytically meaningful only in the context of its Topic.

Examples:

- Doctor → Technology perception: valid.
- Doctor → Farming perception: valid.
- Farmer → Health response: valid.
- Engineer → Agriculture response: valid.

Professional identity does **not** determine the Topic.

A Topic is the subject/domain. Professional identity is context.

## 4. Author context vs respondent lens

These are distinct concepts.

### Author context

Describes the person who created the Perception.

### Respondent lens

Describes legitimate context through which a Response may be aggregated or compared.

The author's professional identity must not automatically be treated as authority over the Topic.

## 5. Initial lenses

Stage 4H supports two concrete lenses:

### Professional lens

Derived from structured, declared professional identity. The current implementation uses the primary professional role for cohorting.

### Geographic lens

Derived from structured location. The current implementation supports country and region. City-level aggregate intelligence is excluded.

Future lenses may include other legitimate contextual dimensions, but a user attribute must not become a lens merely because it exists. A dimension should be surfaced only when it materially explains a meaningful difference and can be used legitimately and safely.

## 6. Privacy and sample rules

Aggregate intelligence must not expose individual participant identities.

The minimum analytical cohort is **5 observations**. Cohorts below the minimum are suppressed.

No city-level aggregate reporting is part of this contract.

The platform must not infer protected or sensitive characteristics from response text, behaviour, professional identity, geography, or other indirect signals.

## 7. Evidence envelope

Every meaningful analytical output must be traceable to an evidence envelope containing, where applicable:

- Topic
- Perception
- Scope
- Time period
- Lens
- Sample size
- Observed evidence
- Quality / confidence indicator
- Limitations

The system must distinguish observed evidence from interpretation and from potential implications.

## 8. Semantic interpretation

The current semantic layer may produce:

- sentiment — feeling toward the discussion
- stance — relationship to the proposition (supportive, challenging, mixed, unclear)
- themes
- questions
- concerns
- agreement signals
- disagreement signals

Sentiment and stance are not interchangeable.

## 9. Pattern

A **Pattern** is an observable relationship in the evidence.

Examples:

- a theme repeatedly appearing within a professional cohort
- a theme occurring differently across geographic cohorts
- convergence between professional cohorts
- divergence between professional cohorts
- a temporal change in an observed signal

A pattern is not automatically causal or representative of a wider population.

## 10. Signal

A **Signal** is a sufficiently meaningful pattern that the product chooses to surface.

A signal must retain its evidence context. It must not be presented as a universal conclusion.

Example framing:

> Among the observed farmer responses, affordability appeared repeatedly.

Preferred over:

> Farmers will not adopt the product because of price.

The second statement makes a stronger predictive/causal claim than the evidence supports.

## 11. Potential implication

An implication is a reasoned interpretation of why an observed signal may matter.

Implications must remain explicitly scoped and non-causal unless causal evidence exists outside the platform's ordinary observational data.

Example:

> The recurring affordability concern may warrant further investigation of pricing and access.

Not:

> Reducing price will increase adoption.

## 12. Decision Context

Decision Context reframes the same evidence for a legitimate human decision intent without changing the underlying facts.

Initial decision intents:

- Research / hypothesis exploration
- Business / market exploration
- Policy / public-interest exploration
- Journalism / narrative exploration
- Education / learning exploration
- Product / product-management exploration
- Professional exploration
- General exploration

The underlying evidence remains invariant. Only the decision framing changes.

## 13. Intelligence layers

### Layer A — Raw measurements

Direct platform observations such as responses, interactions, dates, and structured participant context.

### Layer B — Descriptive analytics

Counts, rates, participation, distributions, and time-bounded measurements.

### Layer C — Audience composition

Aggregate professional and geographic composition subject to privacy and sample rules.

### Layer D — Semantic interpretation

Sentiment, stance, themes, questions, concerns, agreement and disagreement signals.

### Layer E — Cross-dimensional perspectives

Comparison of qualifying professional, geographic, and future legitimate lenses.

### Layer F — Temporal patterns

Changes in observed participation or semantic patterns over defined periods.

### Layer G — Evidence-backed implications

Carefully scoped interpretations derived from observed patterns.

### Layer H — Decision Context

Decision-oriented framing of the evidence for the selected intent.

## 14. Persistence boundary

The following are existing or legitimate persisted domain data:

- Topic
- Perception
- Comment / Response
- User
- Professional identity
- Geographic context
- CommentIntelligence

The following are initially **derived analytical concepts**, not mandatory database entities:

- Evidence
- Pattern
- Signal
- Potential Implication
- Decision Context

They may become persisted objects later only when product requirements demonstrate a need for historical versioning, auditability, workflow, or reuse.

## 15. Current Stage 4H implementation boundary

The existing CommentIntelligence worker remains the **evidence-generation / semantic analysis layer**.

Current Stage 4H professional, geographic, and professional × geographic semantic analysis remains the first concrete lens implementation.

The next implementation layer must be deterministic intelligence/domain orchestration around those outputs. It must not replace the existing evidence-generation layer or add another LLM capability merely to generate conclusions.

## 16. Frontend contract

Perception Intelligence answers:

1. What happened?
2. Who participated, in aggregate?
3. What are people saying?
4. Which professional perspectives are visible?
5. Which geographic perspectives are visible?
6. Where do perspectives converge or diverge?
7. What patterns are emerging?
8. What evidence-backed signals may matter?
9. What decision context is relevant?

Profile Intelligence answers the longitudinal question:

> What is happening across my perceptions, topics, participation, and observed audience patterns over time?

Topic Intelligence is a future surface and is not part of the immediate implementation scope.

## 17. Monetization contract

Monetization is based on **intelligence depth and scope**, not vanity metrics or raw AI-request counts.

Capability progression:

```text
Participate
   ↓
Understand one Perception
   ↓
Understand a Profile / portfolio
   ↓
Explore cross-lens intelligence
   ↓
Explore multiple perceptions / broader scopes
   ↓
Decision-oriented professional intelligence
   ↓
Organization / project intelligence (future)
```

Exact plan limits are deliberately deferred until capability enforcement and actual infrastructure economics are implemented and measured.

## 18. Non-negotiable product principles

1. Topic is first-class.
2. Topic and professional identity are orthogonal.
3. A response is evidence; an AI conclusion is not evidence.
4. Differences between legitimate lenses are themselves analytically meaningful.
5. Individual participant identities are not exposed through aggregate intelligence.
6. Minimum cohort size is 5.
7. City-level aggregate intelligence is excluded.
8. Sensitive traits are not inferred.
9. Observational platform data must not be presented as causal proof.
10. Population-level claims require appropriate external evidence; platform observations alone do not establish representativeness.
11. Decision Context changes framing, not facts.
12. Every meaningful signal remains traceable to evidence, sample, scope, period, quality, and limitations.
13. New lenses are added only when they have legitimate data, material analytical value, and a defensible privacy/safety basis.
14. The platform should surface multiple perspectives rather than manufacture a single universal AI conclusion.
