# Discovery 20 — Conversation Quality Intake

## Product intent

Perception is a conversation platform, not an attention-maximizing social feed. A new Perception must belong to a Topic and should enter the public conversation only after a conservative intake check.

## Intake model

```text
Compose Perception
      ↓
Choose Topic
      ↓
Conversation Quality Guard
      ├── no strong signal → publish
      └── multiple independent signals → pending review
                                      ↓
                              human admin review
                               ↙             ↘
                           approve          remove
```

The guard is deliberately narrow. It checks observable spam/privacy-risk patterns such as link-heavy submissions, contact information, repetitive content, excessive caps, and extremely low variation. It does **not** determine whether a viewpoint is true, false, important, political, offensive, or valuable.

A single weak signal does not hold a post. Multiple independent signals are required for an automatic review hold.

## Privacy and trust

- Pending perceptions are excluded from public feeds, search, recommendations, related perceptions, related topics, and related creators.
- The author receives a clear review message; other users do not see moderation metadata.
- Admin review records the decision and machine-observed flags in the administrative audit trail.
- Report data remains separate from intake assessments.
- No LLM/provider call is made in the request path.
- No participant identity or analytics intelligence is used by the intake guard.

## Product UX

The composer is intentionally focused:

1. Explain what a Perception is.
2. Ask for the thought.
3. Make Topic selection visually prominent.
4. Allow optional media.
5. Explain the quality check without threatening or judging the author.
6. Use `Add to conversation` as the primary action.

This is a quality gate, not a content-ranking mechanism.

## Future semantic review

The guard is intentionally deterministic for now. If a future semantic safety provider is introduced, it must remain an explicit processing layer with minimized payloads, auditable outcomes, and human review for consequential decisions. It must not become the source of truth for a person's viewpoint or automatically suppress ordinary disagreement.
