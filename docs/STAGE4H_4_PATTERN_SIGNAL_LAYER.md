# Stage 4H.4 — Evidence-backed Pattern & Signal Layer

## Purpose

Populate the `patterns` and `signals` sections of `PerceptionIntelligence` using deterministic application logic over already-qualified aggregate semantic evidence.

## Rules

- No LLM/provider call is made by this layer.
- No individual participant identity is returned.
- No causal or predictive claim is generated.
- No pattern or signal is emitted when the semantic sample is below the minimum of 5 analyzed comments.
- Signals carry the supporting sample size and limitations.
- Decision context receives the same observed signals; it does not alter their evidence.

## Current deterministic patterns

- Dominant sentiment
- Dominant stance
- Recurring theme
- Question activity
- Concern theme
- Mixed response signals when agreement and disagreement signals coexist
- Multiple qualifying professional/geographic perspectives

These are descriptive observations, not explanations of why a response occurred.
