# Sprint 2.5 — Geographic Context

## Objective
Make broad, user-provided geographic context available as a personalization and creator-context signal without introducing silent device-location tracking or unexpected public disclosure.

## Contract
- Country, region, and city are explicit profile fields supplied by the user.
- No GPS coordinates or background device location are collected by this feature.
- City is never exposed through the public creator profile.
- Public location display is controlled by `privacy_preferences.location_visibility`: `private`, `country`, or `region`.
- Existing analytics geography continues to use country/region/city internally where its existing entitlement and intelligence contracts permit it.
- Public creator profiles receive only a derived `location_label`, never raw `country_code`, `region`, or `city`.
- Existing privacy invariants continue to forbid raw location fields in public schemas.

## Product flow
`User-provided context → privacy choice → derived public label (optional) → future personalization`

## Onboarding
`Topics → Professional Identity → Geographic Context → Verification`

Geographic context can be skipped. Skipping leaves the default visibility private.

## Acceptance
- User can save country/region/city independently of analytics subscription.
- User can choose private, country-only, or country+region public visibility.
- Public profile never renders city.
- Public profile never renders raw geographic fields.
- Existing analytics profile remains backward compatible.
- No location permission or device geolocation API is introduced.
