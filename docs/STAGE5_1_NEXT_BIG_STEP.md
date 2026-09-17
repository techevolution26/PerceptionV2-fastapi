# Next Big Step — Stage 5.1 Topic Intelligence

## Position

Stage 4H is the frozen Core Intelligence Foundation.

The next major capability is:

> **Stage 5.1 — Topic Intelligence**

It expands intelligence from **one Perception** to a qualified set of **Perceptions belonging to one Topic**.

## Product progression

```text
Topic
  ↓
Multiple Perceptions
  ↓
Human Responses
  ↓
Existing CommentIntelligence
  ↓
Evidence
  ↓
Cross-Perception Patterns
  ↓
Topic Signals
  ↓
Decision Context
```

## What Stage 5.1 must NOT do

It must not:

- create a second semantic engine;
- make a new LLM request simply to summarize a Topic;
- expose participant identities;
- expose city-level aggregate intelligence;
- infer sensitive traits;
- claim causation;
- claim population-wide representation;
- introduce predictive claims;
- weaken existing entitlement controls;
- modify the frozen 4H evidence/provenance/governance contracts.

## Qualification

A response qualifies only when its existing CommentIntelligence is analyzed and governed.

A Perception qualifies for Topic breadth only when it has at least:

- 5 analyzed responses in the selected period.

Topic-wide conclusions require at least:

- 2 independently qualifying Perceptions;
- 5 unique active participants.

These are separate privacy/evidence gates.

## Initial scope

One Topic:

- active Perceptions attached through persisted `topic_id`;
- bounded period, default 180 days;
- minimum 30 days;
- maximum 365 days;
- analyzed responses only;
- existing quality/freshness/model governance;
- existing professional/geographic lenses.

## Initial endpoint direction

Preferred resource boundary:

`GET /api/topics/{topic_id}/intelligence`

The existing contract work in:

- `STAGE5_1_0_TOPIC_INTELLIGENCE_CONTRACT_LOCK.md`
- `STAGE5_1_1_TOPIC_EVIDENCE_SCOPE.md`
- `STAGE5_1_TOPIC_INTELLIGENCE_FOUNDATION.md`

is the design source for implementation.

## Implementation order

```text
5.1.0 Contract Lock
        ↓
5.1.1 Evidence Scope & Participant Privacy
        ↓
5.1.2 Topic aggregation service
        ↓
5.1.3 Topic Intelligence API
        ↓
5.1.4 Topic patterns/signals
        ↓
5.1.5 Topic cross-lens intelligence
        ↓
5.1.6 Topic temporal intelligence
        ↓
5.1.7 Topic decision context
        ↓
5.1.8 Topic provenance/governance
        ↓
5.1.9 Topic access/free tier
        ↓
5.1.10 Acceptance/regression gate
```

Each slice must preserve the 4H contracts.

## Decision principle

The same evidence must remain the same regardless of decision intent.

Research, business, policy, journalism, education, product, professional, and general exploration may change the framing, but not the evidence.

## Release principle

Do not call Stage 5.1 production-ready merely because the endpoint works.

It needs:

- authorization verification;
- privacy verification;
- minimum-sample tests;
- participant suppression tests;
- provenance tests;
- stale/pending/failed evidence tests;
- model-governance tests;
- free/full entitlement tests;
- mobile UI verification;
- regression against the frozen 4H contract.

## Why this is the next big step

A single Perception tells us what happened around one proposition.

Topic Intelligence lets us ask the next-level question:

> **What patterns remain visible when multiple Perceptions about the same Topic are considered together?**

That is the first major expansion of analytical scope after the frozen Core Intelligence Foundation.
