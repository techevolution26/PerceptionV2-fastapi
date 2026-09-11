# Stage 4H.20 — Production Acceptance Gate

## Purpose

Stage 4H.20 is the production acceptance and freeze gate for the core Perception Intelligence Layer.
It does not remove the ability to build higher-level capabilities afterward. It establishes that the current intelligence foundation is coherent, privacy-safe, contract-stable, and ready to serve as a production base.

## Production gate principles

- Human responses remain the evidence source.
- AI interpretation is a derived layer, not primary evidence.
- Minimum analytical sample is 5.
- Pending and failed semantic analysis are excluded from qualified intelligence.
- Signals require qualifying evidence and current freshness.
- City-level aggregate intelligence is not exposed.
- Individual participant identities are not exposed through intelligence aggregates.
- Observer intelligence does not expose creator-only views, shares, engagement rate, or daily activity.
- Free intelligence is intentionally bounded to a teaser.
- Creator analytics, profile intelligence, and comparative intelligence require analytics entitlement.
- AI response status is exposed only to the authorized perception owner with analytics entitlement.
- Decision context reframes evidence; it does not establish causation, prediction, scientific proof, or population representativeness.

## Automated gate

Run from the backend directory against the dedicated acceptance environment:

```bash
pytest -m acceptance tests/acceptance
```

The production intelligence gate additionally requires:

```text
ACCEPTANCE_BASE_URL
ACCEPTANCE_ANALYTICS_EMAIL
ACCEPTANCE_ANALYTICS_PASSWORD
ACCEPTANCE_INTELLIGENCE_PERCEPTION_ID
```

For comparative intelligence coverage, also provide:

```text
ACCEPTANCE_COMPARATIVE_PERCEPTION_IDS=123,456
```

The configured intelligence perception should be an active perception owned by the analytics acceptance account. It should be representative of the deployed intelligence contract and may have either sufficient or insufficient semantic sample; both are valid contract states.

## Required runtime checks

### Core contract

- `/api/analytics/perceptions/{id}` returns the complete nested `PerceptionIntelligence` contract.
- Author receives `viewer_lens=author` and `access_tier=full` when entitled.
- Observer receives `viewer_lens=observer` and conversation-intelligence scope.
- Free observer receives `access_tier=free_teaser` with bounded intelligence.

### Evidence governance

- Minimum sample remains 5.
- Quality threshold remains 0.60.
- Freshness state is explicit.
- Patterns/signals are gated by evidence governance.
- Provenance is present.

### Semantic governance

- Model governance state is present.
- Model-version comparison is explicit when sufficient samples exist.
- Review-required and insufficient-sample states remain representable.

### Temporal and longitudinal intelligence

- Temporal windows remain non-interpolated.
- Longitudinal profile intelligence remains restricted to the authenticated owner's portfolio.

### Comparative intelligence

- 2–5 unique perceptions can be compared only within the authenticated owner's portfolio.
- Analytics entitlement is required.

### AI transparency

- AI analysis status is visible only to the perception owner with analytics entitlement.
- Non-owners receive `null` AI status.
- Free owners receive no AI-status exposure.
- Comments and replies preserve the existing far-right AI badge presentation.

### Security

- Authentication and token-version revocation remain enforced.
- Suspended accounts remain blocked.
- Admin boundaries remain intact.
- Private realtime authorization remains intact.
- Production configuration remains fail-closed.
- Rate limiting and provider cooldown remain active.

## Mobile release gate

The mobile app is accepted only when the following are verified on the target Android device:

- cold start/auth restoration
- login/register/logout
- feed/discover/profile navigation
- Perception detail and comments
- comment/reply creation
- AI badge owner/subscriber visibility
- AI badge absence for non-owner/free users
- Perception Intelligence screen
- free teaser state
- full analytics state
- profile intelligence
- comparative intelligence
- messaging and notifications
- realtime updates
- keyboard/modal behavior
- no TypeScript errors

## Freeze decision

When the automated and manual checks pass, Stage 4H is considered a stable production foundation.

After the gate, new work should be implemented as higher-level capabilities on top of the frozen contracts rather than by casually changing the evidence model.

The next layer may include broader Topic Intelligence, portfolio/market intelligence, richer decision workflows, organizational/project intelligence, or other product capabilities, but those should consume the established evidence, provenance, governance, privacy, and entitlement contracts.
