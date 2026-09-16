# Sprint 2.4 — Rich Creator Profile Foundation

## Objective
Turn the existing public user profile into a richer creator identity surface without exposing private analytics, precise location, or unsupported intelligence.

## Contract
- Public creator profiles expose existing public identity, professional identity, followed-topic context, engagement counts, and published perceptions.
- Professional identity and verification remain separate signals.
- Verification uses the established contract: `VERIFIED` plus at least one `verified_professional_roles` entry, with a professional role available for the badge surface.
- Followed topics are read from the existing public `/api/users/{user_id}/topics` contract.
- No new private analytics fields are exposed by this sprint.
- No precise geographic location is added to the public profile by this sprint.
- No engagement ranking or intelligence score is introduced.

## Profile progression
`Identity → Professional context → Topics → Perceptions`

The existing profile counts and perception history remain the source of truth for activity. This sprint adds contextual presentation; it does not create a second creator-data model.

## Acceptance
- Public profile loads identity, perceptions, and followed topics from existing endpoints.
- Professional role/industry context is visible when present.
- Followed topics are visible when present and link to their topic pages.
- Verification remains governed by the existing professional-verification contract.
- Empty professional/topic data produces a clean profile state.
- No private analytics or precise location is rendered through this foundation.
