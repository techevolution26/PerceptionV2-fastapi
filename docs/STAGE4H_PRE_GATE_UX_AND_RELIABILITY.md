# Perception — Pre-4H.20 UX & Reliability Hardening

## Included

- Fixed free-tier Perception Intelligence response validation: the decision context keeps the locked `available` / `insufficient_sample` contract while free-tier limits remain explicit in the summary and limitations.
- Added persisted notification preferences and future-notification gating.
- Added contextual mobile Privacy, Help & Support, and About Perception surfaces.
- Corrected onboarding progression: Topics → Professional Identity → optional Professional Verification → Home.
- Added contextual setup guidance and explicit skip/later paths.
- Verification evidence/context now explicitly accepts relevant public evidence links while warning users not to submit credentials or private secrets.
- Removed a stale verification-route reference to an undefined analytics topic list.

## Boundaries

- No new topic-intelligence layer is introduced here.
- Verification remains a reviewed professional signal and subscription capability.
- Privacy copy does not claim controls that are not enforced by the server.
- Notification preferences affect future notifications; existing notifications remain intact.
