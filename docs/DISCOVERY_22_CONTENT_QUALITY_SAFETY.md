# Discovery 22 — Content Quality & Safety Controls

## Purpose

Perception treats content quality as conversation hygiene, not viewpoint scoring.
A new perception must belong to a Topic and pass observable intake checks before
it enters the public conversation.

## Intake contract

1. Topic is required and must exist.
2. Text is normalized before storage.
3. Empty text is rejected.
4. Text is bounded at 2,000 characters.
5. Media remains optional.
6. The deterministic intake guard may flag observable spam/privacy-risk patterns.
7. A single flag does not automatically hold a perception.
8. Multiple independent signals create `pending_review`.
9. Human moderation remains authoritative for held content.

## Current observable signals

- `link_heavy`
- `contact_information`
- `repetitive_content`
- `excessive_caps`
- `low_variation`

These signals do not claim that a viewpoint is true, false, useful, offensive,
political, or otherwise valuable.

## Public-surface isolation

`pending_review` perceptions are excluded from public perception retrieval and
discovery surfaces until approved. Removed perceptions remain excluded.

## Product principle

Do not add an automated “quality score” to rank people or viewpoints. Quality
controls exist to keep conversations usable and protect people, while discovery
and intelligence remain contextual rather than popularity-driven.
