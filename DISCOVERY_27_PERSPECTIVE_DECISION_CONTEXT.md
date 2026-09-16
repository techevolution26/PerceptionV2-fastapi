# Discovery 27 — Perspective & Decision Context

## Purpose

Stage 27 builds directly on Perception Intelligence. It does not create another semantic engine, ranking model, or analytics dashboard.

The product question becomes:

> Given the evidence already observed in this conversation, what perspective or decision context would help the person investigate it further?

## Product flow

```text
Conversation
    ↓
Qualified intelligence
    ↓
Patterns / signals
    ↓
Perspective lens
    ↓
Decision context
    ↓
Independent validation / next investigation
```

## Rules

- The existing Perception Intelligence endpoint remains the source of truth.
- The selected lens may change relevance and next-step framing, but it must not change evidence, samples, periods, cohort definitions, or observed measurements.
- No causal, predictive, population-wide, or motivational conclusions are generated.
- No participant identity is exposed.
- No city-level aggregate is introduced.
- No synchronous AI/provider call is introduced.
- Free access remains bounded to the existing teaser contract.
- Deeper perspective and decision framing remain analytics-entitled.
- The conversation UI shows at most one decision observation at a time to preserve the conversation-first product principle.

## Supported lenses

`general_exploration`, `research`, `business`, `policy`, `journalism`, `education`, `product`, and `professional`.

These are contextual frames, not recommendations about what the user should decide.

## Acceptance criteria

- A qualified Perception Intelligence view can select a decision lens without changing evidence.
- Changing the lens reuses the existing backend decision-intelligence service.
- The conversation surface remains compact and opt-in.
- Free teaser behavior remains unchanged.
- The UI explicitly communicates the evidence boundary.
- No new semantic/LLM request path exists.
