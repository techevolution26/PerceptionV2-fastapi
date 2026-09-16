# Sprint 2.2 — Topic-selection onboarding

## Objective
Turn topic following into an explicit first-run personalization signal without introducing feed ranking or popularity-based discovery.

## Contract
- New accounts enter the canonical `/topics?onboarding=1` flow.
- Existing accounts are not forced through onboarding.
- Topic state is read from the canonical `GET /api/topics` contract (`followed_by_user`, `followers_count`).
- Follow/unfollow uses the existing canonical topic-follow mutation and optimistic rollback.
- Topic choice is optional; users may skip setup.
- Onboarding state is persisted locally so an interrupted setup can resume after app restart.
- Completing/skipping the final verification step clears the onboarding-pending state.
- No feed ranking is performed from topic follows in this sprint.

## Verification identity correction
The mobile verified mark is now driven by the authoritative `verification_status === VERIFIED` state. A verified account can therefore display the verification mark even if its verified-role list is empty due to legacy/incomplete data. Professional role icons retain their industry colors; the verified mark uses a dedicated trust color.

## Acceptance
- Topic selection loads authenticated follow state.
- Follow/unfollow remains idempotent and concurrency-safe.
- Optimistic selection rolls back on failure.
- Onboarding can resume after app restart.
- Existing users are not redirected into onboarding.
- Verified individuals display a visible check-decagram across supported identity surfaces.
