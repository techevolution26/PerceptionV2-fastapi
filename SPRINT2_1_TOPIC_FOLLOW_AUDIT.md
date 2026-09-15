# Sprint 2.1 — Topic Following Audit & Hardening

## Status

**Implementation complete; acceptance testing is environment-dependent.**

## What changed

### Topic-following contract

- `TopicOut` now carries the public aggregate `followers_count` and the viewer-specific `followed_by_user` state.
- `GET /api/topics` returns follower counts and personalized follow state when a valid bearer token is supplied; anonymous requests remain supported.
- `GET /api/topics/{topic_id}` returns the same state for topic detail pages.
- The existing composite primary key on `topic_follows (user_id, topic_id)` remains the persistence-level duplicate guard.
- Follow creation now treats a concurrent duplicate insert as an already-successful desired state instead of surfacing a server error.

### Mobile synchronization

- Topic lists use the canonical `TopicOut.followed_by_user` state instead of making a second request to reconstruct it.
- Topic onboarding uses the same canonical state.
- Topic detail now exposes Follow/Following state and follower count.
- Topic detail follow is optimistic, guarded against double submission, updates the follower count locally, and rolls back on failure.
- Topic follow success/failure is surfaced through the global toast system.

## Verification identity visibility

The reusable `VerifiedBadge` was strengthened so verification remains visible even when a verified user has no primary professional role selected. In that case the UI renders the verification check directly rather than requiring a role icon.

The verified signal is now consistently surfaced in:

- Perception cards
- Public profiles
- Follower/following profile lists
- Perception comments
- Message search results
- Conversation list

Verification remains backend-authoritative: the UI only treats a person as verified when `verification_status == VERIFIED` and at least one `verified_professional_roles` entry exists.

## Validation

- Backend `python -m compileall -q app alembic`: **PASS**
- Modified mobile TS/TSX syntax/transpile validation: **PASS**
- Full mobile `tsc --noEmit`: **not executed here** because the release ZIP intentionally excludes `node_modules`.
- Backend pytest: **blocked in this environment** because the runtime lacks `asyncpg` (and the SQLite test fallback lacks `aiosqlite`).

## Product boundary

Sprint 2.1 does **not** introduce feed ranking. Topic following is now a reliable personalization signal that can be consumed by the later Discovery stages without turning popularity into importance.
