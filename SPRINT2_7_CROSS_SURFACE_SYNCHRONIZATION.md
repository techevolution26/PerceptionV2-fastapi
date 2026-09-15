# Sprint 2.7 — Cross-surface Synchronization

## Objective
Keep personalization, topic-follow, identity, location, and perception action state aligned across product surfaces without creating a second source of truth.

## Contract
- Backend remains canonical for persisted state.
- React Native action hooks remain the canonical mutation layer.
- Shared perception state is updated immediately after successful like/save mutations.
- Topic and user follow mutations invalidate the relevant React Query caches.
- Focused screens rehydrate from the canonical API when they become active again.
- Search requests use the authenticated viewer when available so like/save state is serialized for the current user.
- Geographic context remains governed by the existing public-location visibility contract.
- No new popularity score or intelligence layer is introduced.

## Surfaces
Home, Topic index/detail, Saved, Search, Perception detail, creator profile, onboarding, and professional identity consume the same backend state and refresh rules.

## Acceptance
A state changed on one surface must be reflected when another affected surface becomes active, while the current surface receives immediate optimistic/canonical mutation feedback.
