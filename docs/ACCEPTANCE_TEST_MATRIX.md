# Perception — End-to-End Acceptance Test Matrix

This is the **Stage 3 release gate**. The purpose is to validate user-visible workflows across the FastAPI API, PostgreSQL/Redis/Soketi stack, and the Expo mobile client rather than treating individual endpoint tests as sufficient.

## Gate rules

- Run against a **dedicated acceptance/staging environment**, never production data.
- PostgreSQL, Redis, and Soketi must be running for the backend acceptance suite.
- Authentication rate limits may be raised only in the dedicated acceptance environment so the test run itself is not mistaken for an attack.
- Every **FAIL** blocks release.
- **SKIP** is allowed only for flows that require an external provider or physical device and must be completed manually before release.
- A green automated API suite does not replace the mobile and realtime manual checks.

## Automated backend/API gate

Run from the backend root:

```bash
pytest tests/acceptance/ -v -m acceptance
```

Required environment:

```bash
export ACCEPTANCE_BASE_URL=http://localhost:8000
export ACCEPTANCE_ADMIN_EMAIL=...
export ACCEPTANCE_ADMIN_PASSWORD=...
export ACCEPTANCE_PLATFORM_ADMIN_EMAIL=...
export ACCEPTANCE_PLATFORM_ADMIN_PASSWORD=...
```

Optional external-flow credentials:

```bash
export ACCEPTANCE_GOOGLE_EXISTING_ID_TOKEN=...
export ACCEPTANCE_GOOGLE_NEW_ID_TOKEN=...
export ACCEPTANCE_ANALYTICS_EMAIL=...
export ACCEPTANCE_ANALYTICS_PASSWORD=...
```

Use a unique run identifier when repeating against the same acceptance database:

```bash
export ACCEPTANCE_RUN_ID=$(date +%Y%m%d%H%M%S)
```

## Matrix

| Area | Test | Automated | Manual / external | Release expectation |
|---|---|---:|---:|---|
| Auth | Register → login → logout | ✅ | | Old token is rejected after logout |
| Auth | Google → existing account | ⚠️ | Google credential required | Existing local account is linked safely |
| Auth | Google → new account | ⚠️ | Google credential required | New account is created and authenticated |
| Auth | Suspended account rejected | ✅ | | Login returns 403 |
| Content | Create → edit → visible in feed | ✅ | | Updated content is visible; Perception has no separate publish endpoint |
| Content | Like → unlike | ✅ | | State and count change correctly |
| Content | Comment → reply | ✅ | | Reply is attached to correct perception/comment |
| Social | Follow → notification | ✅ | | Follow notification is created and unread count increments |
| Messaging | Mutual follow → message | ✅ | | Message blocked until mutual follow |
| Messaging | Edit message | ✅ | | Edit succeeds inside 15-minute window |
| Messaging | Recall message | ✅ | | Recall succeeds inside 15-minute window |
| Messaging | Archive conversation | ✅ | | Conversation disappears from active list |
| Messaging | Delete conversation | ✅ | | Conversation is hidden for deleting user |
| Notifications | Read/delete/mark-all | ✅ | | Current API supports delete + mark-all; no single-notification read endpoint exists |
| Analytics | Owner sees analytics | ⚠️ | Paid analytics entitlement required | Authorized owner gets 200 |
| Analytics | Non-owner cannot | ⚠️ | Paid analytics account required | Unentitled user gets 402 |
| Admin | SUPER_ADMIN enters control room | ✅ | | Admin session + admin token work |
| Admin | Admin cannot access SUPER_ADMIN endpoints | ✅ | | User-scoped token gets 403 |
| Admin | Suspend/restore user | ✅ | | Suspension blocks login and restore re-enables it |
| Realtime | Private notification channel authorization | ✅ | | Own channel 200; another user's channel 403 |
| Realtime | Message/update/notification events actually arrive | | ⚠️ | Verify on two connected clients through Soketi |
| Mobile | Cold start/auth persistence | | ⚠️ | Token survives app restart; invalid token clears session |
| Mobile | Android navigation/keyboard/modals | | ⚠️ | No clipping, keyboard overlap, broken modal/back behavior |

## Manual realtime gate

1. Log in as Alice on one client and Bob on another.
2. Ensure both follow each other.
3. Send a message from Alice.
4. Confirm Bob receives it without refreshing.
5. Edit the message and confirm the update arrives.
6. Recall the message and confirm the recalled state arrives.
7. Have Alice follow a third account or trigger another supported notification.
8. Confirm the notification arrives without refreshing.
9. Disconnect/reconnect one client and confirm the realtime connection recovers.

## Manual Android gate

On the target Android device:

1. Fresh install → launch → verify unauthenticated state.
2. Register/login → force-close → reopen → verify authenticated state is restored.
3. Navigate through Home, Discover/Search, Notifications, Messages, Profile, and Control Room where applicable.
4. Open text inputs with the keyboard visible; verify fields/buttons are not obscured.
5. Open and dismiss action menus/modals; verify Android back behavior.
6. Send/edit/recall a message while the keyboard is open.
7. Log out → force-close → reopen → verify the auth state is cleared.

## Final sign-off

Release is **PASS** only when:

- Automated acceptance tests pass.
- Google flows have been completed if Google sign-in is enabled for the release.
- Analytics owner/non-owner behavior has been completed against an entitled acceptance account.
- Realtime message/update/notification delivery has been observed on connected clients.
- Android cold-start, keyboard, navigation, and modal checks pass.
- No unexplained 4xx/5xx occurs in a normal user flow.
