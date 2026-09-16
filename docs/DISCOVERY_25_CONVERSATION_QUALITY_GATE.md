# Discovery 25 — Conversation Quality Gate

This stage is an acceptance and hardening gate, not a new user-facing discovery surface.

## Required contracts

- Every Perception belongs to a chosen Topic.
- New Perception intake may place suspicious submissions into human review.
- Pending-review content is excluded from public discovery surfaces.
- Reports are private and do not expose reporter identity.
- Rate limits slow abusive throughput without creating a long-term behavioral profile.
- Verification describes reviewed professional identity and does not certify individual statements.
- Geographic personalization uses only explicitly permitted broad geography; city/GPS is not used.
- Intelligence participation follows the user's privacy preference.
- Creator discoverability follows the creator's privacy preference.
- Public schemas do not expose credentials, billing identifiers, private analytics fields, or precise location.
- Aggregate intelligence requires the minimum analytical sample and does not expose participant identity.
- Recommendation and discovery ranking do not use global popularity metrics.
- Related Perceptions are user-initiated after meaningful engagement and sustained attention; they are not injected into the default conversation view.
- No LLM/provider call is required in the synchronous Perception creation or discovery request path.

## Release gate

Backend source compilation must pass. Database migrations must import all model metadata successfully. Mobile TypeScript validation must pass in the project's installed dependency environment. Full integration tests should pass when the test environment includes all declared database drivers and services.

This gate must be green before expanding the Perception Intelligence surface.
