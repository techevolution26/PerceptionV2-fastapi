# Discovery 29 — Evidence Trace & Verification Context

## Purpose
Make Perception Intelligence inspectable. A user should be able to see where an observed pattern came from, how much qualifying evidence supports it, what period it covers, and what limitations apply before using an investigation path.

## Product rule
Evidence traceability explains the existing evidence chain. It does not expose participant identities, raw private data, hidden prompts, provider internals, or create a new evidence source.

## Trace contents
- trace identifier
- evidence source
- evidence types
- qualifying sample size
- analysis period
- qualification statement
- limitations

## Privacy
The trace is aggregate and scoped to the existing intelligence contract. No participant identity, city/GPS information, or private geographic detail is exposed.

## UX
Evidence details remain collapsed by default inside Perception Intelligence. The user expands them when they want to inspect the basis of a pattern or signal. This keeps the conversation primary while making the intelligence auditable.

## Decision boundary
The trace does not make a claim stronger merely because a trace exists. Investigation paths still point toward independent validation, and decision context cannot modify the underlying evidence.
