# Perception API (FastAPI)

A ground-up rewrite of the original Laravel API — same domain model and the
same wire contract the frontend already expects, on a modern async Python
stack.

## Stack

- **FastAPI** (async) + **Uvicorn**
- **SQLAlchemy 2.0** (async) + **Alembic** migrations
- **PostgreSQL 16**
- **Redis** (reserved for caching / future rate-limiting)
- **JWT** bearer auth — slots into the exact `Authorization: Bearer <token>`
  header the frontend already sends; no frontend auth changes needed
- **soketi** — a self-hosted, open-source, Pusher-protocol-compatible
  WebSocket server, so the frontend's existing `laravel-echo` + `pusher-js`
  code keeps working completely unchanged. Only the *server* implementing
  the protocol changed.
- **APScheduler** — runs the daily digest notification job in-process

## Quickstart (Docker)

```bash
cp .env.example .env
# generate a real one: python -c "import secrets; print(secrets.token_urlsafe(64))"
# and paste it in as SECRET_KEY

docker compose up --build
```

That single command builds the image, starts Postgres/Redis/soketi, waits
for the database, runs Alembic migrations, seeds baseline topics and
motivational quotes, and starts the API on **http://localhost:8000**.

- Interactive API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

Point your frontend's `.env.local` at it — see
`perspective-frontend/.env.local.example`. The two `NEXT_PUBLIC_PUSHER_*`
values there must match this backend's `PUSHER_APP_KEY` / `PUSHER_CLUSTER`
exactly, or channel subscriptions will silently fail.

## Local development without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# needs a real Postgres reachable at DATABASE_URL — easiest is:
docker compose up -d postgres redis soketi

cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

## Tests

```bash
pytest tests/ -v
ruff check app/ tests/
```

13 tests, run against an in-memory SQLite database for speed. One route
(`GET /api/conversations`) uses a Postgres-only `DISTINCT ON` query for
efficiency and isn't covered by the fast suite — see the note at the top of
`tests/test_conversations.py` for how to exercise it against real Postgres.

## Project layout

```
app/
  core/        settings, DB engine/session, JWT + password hashing
  models/      SQLAlchemy ORM models (mirrors the schema 1:1)
  schemas/     Pydantic request/response contracts
  services/    file storage, real-time broadcasting, notifications,
               daily digest job, shared perception serialization
  api/routes/  one router per resource, mirroring the old Laravel
               controller grouping
  api/deps.py  DB session + current-user (required and optional) dependencies
  main.py      app wiring: routers, CORS, static file mount, scheduler
alembic/       migrations (hand-authored initial schema)
tests/         pytest suite (see above)
```

## What changed vs. the original Laravel API

Read the whole original codebase (routes, controllers, models, migrations)
before writing anything, to match the real contract — including the Next.js
BFF proxy routes that actually talk to this backend. That surfaced a
handful of genuine bugs, fixed here rather than carried forward:

- **`liked_by_user` was never computed.** The old feed endpoint never told
  the frontend whether the current viewer had liked a perception, so hearts
  always rendered unfilled on load regardless of actual state.
- **Public `/users/{id}` leaked email addresses.** No auth was required on
  that route, but the response included `email`. Fixed: `UserPublic` /
  `UserProfile` never include it; only `UserMe` (your own authenticated
  profile) does.
- **Duplicate, conflicting route registrations.** Several "public" profile
  endpoints (followers, following, etc.) were registered twice in Laravel
  — once behind auth, once public — and the protected one always won,
  meaning a supposedly-public endpoint silently required a token. These are
  genuinely public here, matching what the frontend already does (no
  `Authorization` header sent for these).
- **`topics_count` was missing** from profile stats, even though
  `ProfileSection.jsx` renders it.
- **`/api/conversations` never included `lastMessage` / `lastMessagePreview`**
  even though `ConversationSidebar.jsx` and `ConversationList.jsx` both
  render them. Computed properly here via a single `DISTINCT ON` query.
- **`/api/topics` intentionally still returns `{"topics": [...]}`**, not a
  bare array — confirmed the existing Next.js BFF route already unwraps
  `data.topics`, so this was correct behavior, not a bug. Matched it rather
  than "fixing" something that wasn't broken.
- **Notification channel/event contract redesigned slightly.** The old
  frontend relied on Laravel Echo's `.notification()` sugar method, which
  depends on Laravel-specific internal broadcasting conventions
  (`illuminate:notification`) that a non-Laravel backend can't produce.
  Replaced with a plain, explicit `private-App.Models.User.{id}` channel and
  a `notification` custom event — the frontend's `NotificationsPanel.jsx`
  was updated accordingly (see the frontend patch notes).
- **Two real bugs found in `useMessageStream.js`** while wiring up
  real-time: it was missing `wsHost`/`wsPort` entirely (meaning it would've
  tried to reach real Pusher.com cloud infrastructure instead of this
  self-hosted soketi), and had a hardcoded `forceTLS: true` that breaks
  against local dev's non-TLS soketi. Both fixed — see the frontend patch.
- **The `/api/broadcasting/auth` Next.js proxy route was entirely commented
  out** — a dead route. Every private-channel subscription (the
  notifications feed) silently failed to authorize as a result. Activated.

## Operational notes

- **Daily digest scheduling**: runs in-process via APScheduler, one job per
  API container. Fine for a single instance. If you ever scale to multiple
  API replicas, move this to a dedicated single-instance worker (a separate
  `worker` service in `docker-compose.yml`, or Celery beat) — otherwise
  every replica fires it and users get duplicate notifications.
- **JWT revocation**: tokens are stateless with a 14-day expiry by default
  (`ACCESS_TOKEN_EXPIRE_MINUTES`). There's no server-side revocation list —
  `POST /api/logout` exists for frontend/API-contract parity but doesn't
  invalidate the token early. Add a Redis denylist keyed by token `jti` if
  you need real revocation before expiry.
- **File storage** is local disk under `/app/storage`, persisted via the
  `storage_data` Docker volume and served at `/storage/...` — matching
  Laravel's public-disk URL convention the frontend already expects. Swap
  `app/services/storage.py` for an S3-compatible client if you outgrow a
  single host.
- **Broadcasting is best-effort.** If soketi is unreachable, `POST`
  requests that trigger a broadcast (sending a message, liking, etc.) still
  succeed and persist — the live push just gets logged as a warning and
  skipped. Real-time is an enhancement, never a dependency for correctness.

## Analytics & business model

The FastAPI backend now contains the first production-oriented analytics domain:

- **Plans and subscriptions** — seeded Free, Professional, Research and Business plans, with Stripe price IDs, trial status, billing periods and provider-backed entitlement state.
- **Analytics entitlement** — analytics endpoints return `402 Payment Required` when an account does not have an active analytics-enabled plan. Paid access is granted only after Stripe webhook synchronization; starting Checkout alone never unlocks analytics.
- **Analytics topics** — subscribers can select multiple topic areas while keeping one primary analytics topic/professional focus.
- **Profile geography** — country, region and city fields support geographic coverage analysis.
- **Professional verification** — applications capture profession, focus, primary topic, additional topics and evidence. Approval is intentionally a reviewed workflow rather than an automatic claim.
- **Perception interactions** — authenticated daily-deduplicated VIEW and SHARE events complement the existing LIKE and COMMENT data.
- **Signal methodology** — analytics reports observed engagement indices, sample size and geographic coverage. It explicitly does not present correlation/engagement as scientific proof, causation or validated scientific conclusions.
- **Stripe billing** — hosted Checkout for recurring plans, Customer Portal for self-service billing, signed webhook verification, idempotent webhook event storage, renewal/payment-failure synchronization, and invoice history.

Run the migration and seed reference plans:

```bash
alembic upgrade head
python -m app.seed
```


### Stripe configuration

The billing integration is intentionally provider-isolated at the application boundary. Configure the Stripe secret/webhook secret and one recurring Stripe Price ID for each paid plan:

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PROFESSIONAL=price_...
STRIPE_PRICE_RESEARCH=price_...
STRIPE_PRICE_BUSINESS=price_...
STRIPE_SUCCESS_URL=https://your-web-app.example/billing/success
STRIPE_CANCEL_URL=https://your-web-app.example/billing/cancel
```

Then run `alembic upgrade head` and `python -m app.seed`. Stripe Price IDs are stored on the plan rows; the API does not create live products/prices implicitly. Configure the Stripe webhook endpoint at `/api/subscription/webhook/stripe` and subscribe at minimum to `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, and `invoice.payment_failed`.

The mobile app opens Stripe's hosted Checkout URL using the native browser and uses the same authenticated subscription endpoint to determine entitlement after the webhook has been processed. Billing management opens the Stripe Customer Portal.

### Mobile routes

The Expo app now includes:

- `/analytics` — subscriber analytics dashboard.
- `/subscription` — plan/trial and payment boundary screen.
- `/analytics-profile` — professional identity, geography, primary topic and analytics-topic management.
- `/verification` — professional verification application/status.

The analytics icon on each `PerceptionCard` opens `/analytics`. An authenticated user without analytics entitlement is redirected to `/subscription` by the analytics screen.

Administrators (`ADMIN` / `SUPER_ADMIN`) can review verification applications through the verification admin endpoints. Approval writes the reviewed badge to the user; rejection does not grant a badge.

## Analytics intelligence layer

The analytics feature now exposes a descriptive intelligence layer on top of perception activity:

- period-over-period topic growth and momentum
- daily perception activity trend
- distinct participant count
- sample-size evidence levels
- strongest and emerging topics
- opportunity signals for patterns worth investigating
- geographic coverage based on profile country fields
- methodology and limitations returned with every analytics response

These outputs intentionally describe observed platform signals. They are not claims of causation, representative population demand, probability, or validated scientific conclusions.

## Security and platform controls

- Password login is rate-limited through Redis and JWTs carry a per-user token version, so logout, suspension, and restoration invalidate previously issued sessions.
- Production responses include baseline security headers and HSTS when `ENVIRONMENT=production`.
- Google sign-in verifies Google identity tokens server-side against configured client IDs; the API never trusts a client-supplied email as proof of identity.
- Public profiles intentionally omit account email/role and expose only presentation and engagement information.
- Messaging is limited to mutual follows for new conversations, supports bounded edit/recall windows, and keeps archive/delete state per user.
- Super-admin control is protected by a separate short-lived admin token obtained through password re-authentication. Administrative user suspension/restoration is audited.
