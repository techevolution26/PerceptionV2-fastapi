# Discovery 24 — Privacy Controls

## Objective

Turn Perception privacy principles into server-enforced user controls without adding surveillance or unnecessary public UI.

## Controls

### Location visibility
- `private` — no public location label.
- `country` — country may be shown publicly and used as an allowed broad personalization context.
- `region` — country and user-provided region may be shown publicly and used as allowed broad context.
- City remains stored only as account context and is not exposed through public profile contracts or used for intelligence aggregation.

### Aggregate intelligence participation
`privacy_preferences.intelligence_participation` defaults to `true` for backward compatibility. When explicitly `false`, the user's comments are excluded from analyzed-comment aggregate intelligence queries, including semantic and temporal aggregates and topic-level semantic aggregation.

This does not delete comments or make them private; it controls their participation in derived aggregate intelligence.

### Creator discovery
`privacy_preferences.creator_discoverability` defaults to `true`. When explicitly `false`, the creator is excluded from contextual Related Creators and creator recommendations while remaining directly accessible through normal profile/content links.

## Enforcement

Preferences are validated server-side. Mobile controls are not security boundaries. Discovery and intelligence queries enforce the preferences at query/aggregation boundaries.

## Non-goals

- No device fingerprinting.
- No GPS tracking.
- No automatic account punishment.
- No inference of sensitive traits.
- No deletion of public social content as a side effect of these controls.

## Release note

The defaults preserve existing behavior for existing accounts. Users can opt out from the Privacy screen.
