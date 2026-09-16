# Discovery 26 — Perception Intelligence Experience

## Purpose

Perception Intelligence is the product layer that turns a sufficiently developed conversation into a compact, evidence-scoped view of what is emerging in that discussion.

It is **not** a conventional AI dashboard and it does not replace the existing semantic intelligence system.

## Product progression

```text
Person asks/shares a perception
        ↓
People respond
        ↓
Conversation develops
        ↓
Enough qualified evidence
        ↓
Perception Intelligence
        ↓
Patterns / perspectives / signals
        ↓
Useful context
```

## Experience gate

The mobile conversation screen does not fetch or display Perception Intelligence on entry.

The invitation becomes available only after:

1. the viewer is authenticated;
2. the viewer has sustained attention in the same Perception for two minutes during the current detail-screen visit; and
3. the viewer has a meaningful interaction with the Perception (like, save, or comment/reply).

The viewer must explicitly switch the intelligence panel on. Leaving the Perception cancels the dwell timer and resets the invitation.

This is a **product/UX gate**, not a security boundary. The server remains authoritative over analytical eligibility and privacy rules.

## Evidence eligibility

The existing intelligence endpoint and semantic engine remain the source of truth. The conversation panel is eligible to show semantic intelligence only when:

- at least 5 comments have completed semantic analysis;
- pending or failed semantic analysis is not treated as evidence;
- intelligence participation/privacy controls remain enforced;
- participant identities are not exposed through aggregates;
- city-level intelligence is not exposed;
- no new LLM/provider call is made in the request path.

When fewer than 5 analyzed comments qualify, the UI shows **Still forming** and the analyzed count rather than inventing a conclusion.

## Display contract

The conversation panel intentionally surfaces only a small number of evidence-backed patterns. It does not put creator metrics, engagement rates, daily activity, geographic breakdowns, or decision dashboards into the main conversation.

Displayed patterns are sourced from the existing `PerceptionIntelligence.patterns` contract. The UI does not rewrite or strengthen the semantic descriptions.

The panel also states the evidence boundary: observed discussion patterns are not proof of causation or population-wide opinion.

## Reuse rule

Do not create a second semantic/AI engine for this stage.

Reuse:

- `CommentIntelligence`
- evidence/provenance contracts
- freshness
- quality
- governance
- cross-lens analysis
- temporal intelligence
- decision intelligence
- privacy participation and creator-discoverability controls

## Acceptance criteria

- Intelligence is absent from the initial conversation view.
- Intelligence becomes discoverable only after the contextual interaction gate.
- Intelligence is opt-in, not auto-expanded.
- Fewer than 5 analyzed comments produces a forming state, not a conclusion.
- Qualified patterns come from the existing backend intelligence contract.
- Leaving the conversation resets the dwell qualification.
- No participant identity is surfaced.
- No city-level aggregate is surfaced.
- No synchronous AI provider call is introduced.
- Existing author analytics remain separate from the conversation experience.
