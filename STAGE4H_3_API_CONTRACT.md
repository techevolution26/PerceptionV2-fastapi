# Stage 4H.3 — API Contract

## Status

Implemented from the frozen Stage 4H.2 Domain Abstraction baseline.

## What changed

- Replaced the flat `PerceptionAnalyticsOut` response with `PerceptionIntelligence`.
- Added explicit `context`, `measurements`, `audience`, `semantic`, `perspectives`, `patterns`, `signals`, `decision_context`, and `methodology` layers.
- Added a typed `decision_intent` query parameter with `general_exploration` as the default.
- Kept creator/observer privacy boundaries intact.
- Kept minimum-sample suppression at 5.
- Preserved professional/geographic/cross-lens semantic analysis.
- Updated the mobile client types and Perception Intelligence screen to consume the nested contract.

## Verification

- Backend `compileall`: passed.
- Direct Pydantic `PerceptionIntelligence` schema validation: passed.
- Backend focused pytest could not start because the execution environment lacks `asyncpg`; this is an environment dependency failure, not a reported test failure.
- Mobile `tsc --noEmit` was not runnable in the packaging environment because `node_modules`/Expo dependencies are not installed; run it in the mobile project environment.
