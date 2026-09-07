import base64
import json
import os

import pytest

from .conftest import Actor, GOOGLE_EXISTING_ID_TOKEN, GOOGLE_NEW_ID_TOKEN, ANALYTICS_EMAIL, ANALYTICS_PASSWORD, auth, register_actor



pytestmark = pytest.mark.acceptance

async def create_perception(api, actor: Actor, topic_id: int, body: str) -> int:
    response = await api.post(
        "/api/perceptions",
        data={"body": body, "topic_id": str(topic_id)},
        headers=auth(actor),
    )
    response.raise_for_status()
    return int(response.json()["id"])


async def login(api, actor: Actor) -> str:
    response = await api.post("/api/login", json={"email": actor.email, "password": actor.password})
    response.raise_for_status()
    return response.json()["token"]


@pytest.mark.asyncio
async def test_auth_register_login_logout(api):
    suffix = os.getenv("ACCEPTANCE_RUN_ID", "release-gate")
    actor = await register_actor(api, name="Acceptance Auth", email=f"acceptance-auth+{suffix}@example.com")
    login_token = await login(api, actor)
    me = await api.get("/api/user", headers={"Authorization": f"Bearer {login_token}"})
    assert me.status_code == 200
    assert me.json()["id"] == actor.user_id

    logout = await api.post("/api/logout", headers={"Authorization": f"Bearer {login_token}"})
    assert logout.status_code == 200
    revoked = await api.get("/api/user", headers={"Authorization": f"Bearer {login_token}"})
    assert revoked.status_code == 401


@pytest.mark.asyncio
async def test_google_existing_and_new_account(api):
    if not GOOGLE_EXISTING_ID_TOKEN or not GOOGLE_NEW_ID_TOKEN:
        pytest.skip("Set both Google ID-token variables to exercise live Google acceptance flows.")

    def unverified_claims(token: str) -> dict:
        parts = token.split(".")
        if len(parts) != 3:
            pytest.fail("Google acceptance token is not a JWT.")
        padding = "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(parts[1] + padding))

    existing_claims = unverified_claims(GOOGLE_EXISTING_ID_TOKEN)
    existing_email = str(existing_claims.get("email", "")).lower().strip()
    if not existing_email:
        pytest.fail("Existing Google acceptance token has no email claim.")

    password = "Acceptance9!Gate"
    local = await api.post(
        "/api/register",
        json={
            "name": "Google Existing Local",
            "email": existing_email,
            "password": password,
            "password_confirmation": password,
        },
    )
    local.raise_for_status()

    existing = await api.post("/api/google", json={"id_token": GOOGLE_EXISTING_ID_TOKEN})
    assert existing.status_code == 200
    assert existing.json()["user"]["email"] == existing_email

    new = await api.post("/api/google", json={"id_token": GOOGLE_NEW_ID_TOKEN})
    assert new.status_code == 200
    assert new.json()["token"]


@pytest.mark.asyncio
async def test_content_create_edit_visible_and_like_unlike(api, actors, topic_id):
    alice = actors["alice"]
    perception_id = await create_perception(api, alice, topic_id, "Acceptance content v1")

    edit = await api.put(
        f"/api/perceptions/{perception_id}",
        data={"body": "Acceptance content v2"},
        headers=auth(alice),
    )
    assert edit.status_code == 200
    assert edit.json()["body"] == "Acceptance content v2"

    feed = await api.get("/api/perceptions")
    assert feed.status_code == 200
    assert any(item["id"] == perception_id and item["body"] == "Acceptance content v2" for item in feed.json())

    like = await api.post(f"/api/perceptions/{perception_id}/like", headers=auth(actors["bob"]))
    assert like.status_code == 200
    assert like.json()["liked"] is True

    unlike = await api.delete(f"/api/perceptions/{perception_id}/like", headers=auth(actors["bob"]))
    assert unlike.status_code == 200
    assert unlike.json()["liked"] is False


@pytest.mark.asyncio
async def test_comment_and_reply(api, actors, topic_id):
    alice = actors["alice"]
    bob = actors["bob"]
    perception_id = await create_perception(api, alice, topic_id, "Comment acceptance")

    comment = await api.post(
        f"/api/perceptions/{perception_id}/comments",
        data={"body": "Root comment"},
        headers=auth(bob),
    )
    assert comment.status_code == 201
    comment_id = comment.json()["id"]

    reply = await api.post(
        f"/api/comments/{comment_id}/replies",
        data={"body": "Reply comment"},
        headers=auth(alice),
    )
    assert reply.status_code == 201

    comments = await api.get(f"/api/perceptions/{perception_id}/comments")
    assert comments.status_code == 200
    assert any(c["id"] == comment_id and c["replies"] for c in comments.json())


@pytest.mark.asyncio
async def test_follow_and_notification_lifecycle(api, actors):
    alice = actors["alice"]
    bob = actors["bob"]

    for actor in (alice, actors["charlie"]):
        follow = await api.post(f"/api/users/{bob.user_id}/follow", headers=auth(actor))
        assert follow.status_code == 200

    notes = await api.get("/api/notifications", headers=auth(bob))
    assert notes.status_code == 200
    data = notes.json()["data"]
    follow_notes = [n for n in data if n["type"] == "follow"]
    assert len(follow_notes) >= 2

    count = await api.get("/api/notifications/unread-count", headers=auth(bob))
    assert count.status_code == 200
    assert count.json()["unread_count"] >= 2

    notification_id = follow_notes[0]["id"]
    deleted = await api.delete(f"/api/notifications/{notification_id}", headers=auth(bob))
    assert deleted.status_code == 200

    # Mark-all remains the supported bulk read contract.
    remaining_count = await api.get("/api/notifications/unread-count", headers=auth(bob))
    assert remaining_count.status_code == 200
    assert remaining_count.json()["unread_count"] >= 1

    read_all = await api.post("/api/notifications/read-all", headers=auth(bob))
    assert read_all.status_code == 200
    count_after = await api.get("/api/notifications/unread-count", headers=auth(bob))
    assert count_after.status_code == 200
    assert count_after.json()["unread_count"] == 0


@pytest.mark.asyncio
async def test_mutual_follow_message_edit_recall_archive_delete(api, actors):
    alice = actors["alice"]
    bob = actors["bob"]

    for follower, followed in ((alice, bob), (bob, alice)):
        response = await api.post(f"/api/users/{followed.user_id}/follow", headers=auth(follower))
        assert response.status_code == 200

    message = await api.post(
        f"/api/conversations/{bob.user_id}",
        json={"body": "Message v1"},
        headers=auth(alice),
    )
    assert message.status_code == 201
    message_id = message.json()["id"]

    edit = await api.patch(
        f"/api/messages/{message_id}",
        json={"body": "Message v2"},
        headers=auth(alice),
    )
    assert edit.status_code == 200
    assert edit.json()["body"] == "Message v2"

    recall = await api.delete(f"/api/messages/{message_id}", headers=auth(alice))
    assert recall.status_code == 200
    assert recall.json()["deleted_at"] is not None

    archive = await api.post(f"/api/conversations/{bob.user_id}/archive", headers=auth(alice))
    assert archive.status_code == 200
    assert archive.json()["archived"] is True

    active = await api.get("/api/conversations", headers=auth(alice))
    assert active.status_code == 200
    assert all(item["id"] != bob.user_id for item in active.json())

    archived = await api.get("/api/conversations?archived=true", headers=auth(alice))
    assert archived.status_code == 200
    assert any(item["id"] == bob.user_id for item in archived.json())

    delete = await api.delete(f"/api/conversations/{bob.user_id}", headers=auth(alice))
    assert delete.status_code == 200
    assert delete.json()["deleted"] is True


@pytest.mark.asyncio
async def test_messaging_is_blocked_without_mutual_follow(api, actors):
    charlie = actors["charlie"]
    alice = actors["alice"]
    response = await api.post(
        f"/api/conversations/{charlie.user_id}",
        json={"body": "Should be blocked"},
        headers=auth(alice),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_analytics_owner_and_non_owner_access(api, actors, topic_id):
    if not ANALYTICS_EMAIL or not ANALYTICS_PASSWORD:
        pytest.skip("Set ACCEPTANCE_ANALYTICS_EMAIL and ACCEPTANCE_ANALYTICS_PASSWORD for analytics release-gate tests.")

    owner_login = await api.post("/api/login", json={"email": ANALYTICS_EMAIL, "password": ANALYTICS_PASSWORD})
    owner_login.raise_for_status()
    owner_token = owner_login.json()["token"]

    owner = await api.get("/api/user", headers={"Authorization": f"Bearer {owner_token}"})
    owner.raise_for_status()
    owner_actor = Actor(
        name=owner.json()["name"],
        email=owner.json()["email"],
        password=ANALYTICS_PASSWORD,
        token=owner_token,
        user_id=int(owner.json()["id"]),
    )
    perception_id = await create_perception(api, owner_actor, topic_id, "Analytics acceptance")

    event = await api.post(
        "/api/analytics/events",
        json={"perception_id": perception_id, "event_type": "VIEW"},
        headers=auth(owner_actor),
    )
    assert event.status_code == 201

    overview = await api.get("/api/analytics/overview", headers=auth(owner_actor))
    assert overview.status_code == 200

    perception_analytics = await api.get(f"/api/analytics/perceptions/{perception_id}", headers=auth(owner_actor))
    assert perception_analytics.status_code == 200

    denied = await api.get(f"/api/analytics/perceptions/{perception_id}", headers=auth(actors["charlie"]))
    assert denied.status_code == 402
    assert denied.json()["detail"]["code"] == "ANALYTICS_SUBSCRIPTION_REQUIRED"


@pytest.mark.asyncio
async def test_super_admin_control_room(api, admin_token):
    overview = await api.get("/api/admin/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert overview.status_code == 200

    audit = await api.get("/api/admin/audit", headers={"Authorization": f"Bearer {admin_token}"})
    assert audit.status_code == 200



@pytest.mark.asyncio
async def test_admin_role_cannot_access_super_admin_control_room(api, platform_admin_token):
    denied = await api.get("/api/admin/overview", headers={"Authorization": f"Bearer {platform_admin_token}"})
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_suspend_restore_and_old_token_revoked(api, admin_token):
    suffix = os.getenv("ACCEPTANCE_RUN_ID", "release-gate")
    target = await register_actor(api, name="Acceptance Suspend Target", email=f"acceptance-suspend+{suffix}@example.com")
    headers = {"Authorization": f"Bearer {admin_token}"}

    suspend = await api.post(f"/api/admin/users/{target.user_id}/suspend", headers=headers)
    assert suspend.status_code == 200

    suspended_login = await api.post("/api/login", json={"email": target.email, "password": target.password})
    assert suspended_login.status_code == 403

    restore = await api.post(f"/api/admin/users/{target.user_id}/restore", headers=headers)
    assert restore.status_code == 200

    restored_login = await api.post("/api/login", json={"email": target.email, "password": target.password})
    assert restored_login.status_code == 200


@pytest.mark.asyncio
async def test_private_notification_channel_authorization(api, actors):
    alice = actors["alice"]
    allowed = await api.post(
        "/api/broadcasting/auth",
        data={"channel_name": f"private-App.Models.User.{alice.user_id}", "socket_id": "acceptance.1"},
        headers=auth(alice),
    )
    assert allowed.status_code == 200

    denied = await api.post(
        "/api/broadcasting/auth",
        data={"channel_name": f"private-App.Models.User.{actors['bob'].user_id}", "socket_id": "acceptance.2"},
        headers=auth(alice),
    )
    assert denied.status_code == 403
