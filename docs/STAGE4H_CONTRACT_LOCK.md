# Stage 4H — Contract Lock

This package freezes the Perception Intelligence / Decision Intelligence domain contract before the next implementation layer.

No database migration, new LLM capability, API redesign, payment-plan enforcement, or frontend feature implementation is introduced by this stage.

The next stage is **Domain / Service Abstraction**, built against this contract and preserving the existing Stage 4H semantic worker and professional/geographic analysis.

## Stage 4H.2 — Deterministic Domain/Service Abstraction

The `app.services.perception_intelligence` module is the first runtime layer above stored semantic evidence. It provides:

- a common evidence envelope carrying topic, perception, scope, period, sample, lens, quality and limitations;
- semantic evidence composition from stored `CommentIntelligence` rows;
- cross-lens evidence wrapping for professional/geographic cohort outputs;
- sample-gated signal qualification;
- decision-context framing that preserves evidence invariance.

This layer makes no LLM/provider calls and does not persist derived signals or implications.
