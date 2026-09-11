# Stage 4H.20 — Production Acceptance Gate

## Purpose

Stage 4H.20 is the release gate for the Perception Intelligence Layer.
It does not add another intelligence feature. It verifies that the intelligence layer can be frozen as a production foundation without violating privacy, authorization, evidence, or operational safety boundaries.

## Gate result

**Application-layer privacy gate: IMPLEMENTED.**

**Production release gate: CONDITIONAL until infrastructure and legal evidence are verified.**

This distinction is intentional. Source-code tests can establish application invariants, but they cannot prove that Railway/Vercel/PostgreSQL/Redis/Soketi/storage, administrator access, backups, DNS/TLS, or third-party contracts are correctly configured.

## Mandatory application controls

### Authorization

- Public endpoints return public identity contracts only.
- Account credentials and billing identifiers remain private.
- Analytics ownership is enforced server-side.
- Observer metrics are suppressed.
- Comparative intelligence is restricted to the viewer's authored perceptions.
- AI response labels are owner/subscription gated.

### Aggregation

- Minimum analytical sample: **5**.
- Small cohorts are suppressed.
- City-level aggregate intelligence is excluded.
- Individual participant identities are never part of aggregate intelligence output.

### AI

- Background worker only.
- Disabled by default.
- External processing requires explicit production configuration.
- Provider payload contains only topic/perception/comment context.
- No participant identity fields are sent to the provider.
- `store=false` is used.
- Provider cooldown/rate-limit handling remains restart-safe.

### Production configuration

Production rejects:

- DEBUG
- weak/default secret
- fail-open rate limiting
- empty CORS
- insecure password-reset URL
- insecure public/Stripe URLs
- insecure AI provider URL
- AI enabled without an API key
- AI enabled without explicit external-processing permission

### API exposure

Production disables interactive API documentation endpoints.
API responses are marked `Cache-Control: no-store` to reduce accidental intermediary/client caching of application data.

### Logging

Do not log:

- passwords
- access tokens
- API keys
- database credentials
- unnecessary sensitive personal data

Security-relevant access-control failures and administrative events should be logged in a protected central logging system.

## Infrastructure acceptance checklist

Before declaring the gate green, verify outside the source tree:

- [ ] Production database is not publicly reachable.
- [ ] Database credentials are stored in the platform secret manager.
- [ ] Redis is not publicly reachable.
- [ ] Uploaded storage is intentionally public only where the product contract says the media is public.
- [ ] TLS is enabled for all public application endpoints.
- [ ] Vercel/Railway environment variables contain no secrets committed to Git.
- [ ] Production CORS contains only the intended web origins.
- [ ] Backups are enabled and access-controlled.
- [ ] Restore procedure has been tested.
- [ ] Admin/SUPER_ADMIN accounts use strong unique credentials and appropriate MFA where supported.
- [ ] CI/CD tokens and GitHub integration have least-privilege access.
- [ ] OpenAI API project data-sharing settings remain disabled unless deliberately approved.
- [ ] OpenAI retention/processing terms are documented for the deployed account.
- [ ] Required data-processing agreements are in place for applicable processors.
- [ ] Privacy notice is published.
- [ ] Terms of service are published.
- [ ] Data retention/deletion policy is defined.
- [ ] User data export/access/deletion workflow is defined where legally required.
- [ ] Incident/breach response procedure is defined.

## Acceptance tests

The automated suite must verify at minimum:

1. Public schemas contain no account credentials or private analytics fields.
2. Observer analytics cannot expose creator-only measurements.
3. Semantic intelligence is withheld below five analyzed observations.
4. Audience breakdowns are withheld below five unique participants.
5. AI payload contains no participant identity/profile attributes.
6. Production cannot enable external AI processing implicitly.
7. Production URLs are HTTPS.
8. Production API documentation is disabled.
9. API responses are marked no-store.
10. Owner/non-owner AI status behavior remains isolated.
11. Comparative intelligence remains restricted to the authenticated owner's perceptions.

## Freeze criterion

4H.20 is complete only when:

- automated application controls pass;
- the owner/non-owner analytics isolation has been manually verified;
- the infrastructure checklist is reviewed;
- privacy notice/terms are published;
- third-party AI processing and retention are documented;
- backup/restore and incident procedures exist.

After that point, the Intelligence Layer can be treated as a stable production foundation.
Higher-level intelligence can be built on top without changing these privacy invariants.
