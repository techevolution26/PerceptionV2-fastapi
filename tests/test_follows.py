# tests/test_follows.py
import pytest

from app.models.models import Topic

pytestmark = pytest.mark.asyncio


async def _register(client, name, email):
    res = await client.post(
        "/api/register",
        json={"name": name, "email": email, "password": "Supersecret1!", "password_confirmation": "Supersecret1!"},
    )
    body = res.json()
    return body["token"], body["user"]["id"]


async def test_follow_and_unfollow_user(client):
    token_a, id_a = await _register(client, "Ada", "ada@example.com")
    _, id_b = await _register(client, "Bob", "bob@example.com")
    headers = {"Authorization": f"Bearer {token_a}"}

    res = await client.post(f"/api/users/{id_b}/follow", headers=headers)
    assert res.status_code == 200

    followers = await client.get(f"/api/users/{id_b}/followers")
    assert followers.status_code == 200
    assert any(u["id"] == id_a for u in followers.json())

    res = await client.delete(f"/api/users/{id_b}/follow", headers=headers)
    assert res.status_code == 200

    followers = await client.get(f"/api/users/{id_b}/followers")
    assert not any(u["id"] == id_a for u in followers.json())


async def test_cannot_follow_self(client):
    token_a, id_a = await _register(client, "Ada", "ada@example.com")
    headers = {"Authorization": f"Bearer {token_a}"}

    res = await client.post(f"/api/users/{id_a}/follow", headers=headers)
    assert res.status_code == 400


async def test_followers_endpoint_is_public_no_auth_required(client):
    """Regression test: the original Laravel routing registered this same
    path twice — once inside an auth-required group, once public — and the
    protected one always won, so a supposedly-public profile endpoint
    silently 401'd for anyone without a token."""
    _, id_a = await _register(client, "Ada", "ada@example.com")
    res = await client.get(f"/api/users/{id_a}/followers")
    assert res.status_code == 200


async def test_profile_includes_topics_count(client):
    """Regression test: Laravel's profile endpoint never computed
    topics_count even though ProfileSection.jsx renders it."""
    _, id_a = await _register(client, "Ada", "ada@example.com")
    res = await client.get(f"/api/users/{id_a}")
    assert res.status_code == 200
    body = res.json()
    assert "topics_count" in body
    assert body["topics_count"] == 0


async def test_topic_follow_is_idempotent_and_topic_exposes_public_count_and_state(client, db_session):
    token, _ = await _register(client, "Ada", "ada-topic@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Create the topic through the test database because topic creation is
    # intentionally outside the public API surface.
    async with db_session() as session:
        topic = Topic(name="Climate", description="Climate perspectives")
        session.add(topic)
        await session.commit()
        await session.refresh(topic)
        topic_id = topic.id

    first = await client.post(f"/api/topics/{topic_id}/follow", headers=headers)
    second = await client.post(f"/api/topics/{topic_id}/follow", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["followed"] is True
    assert second.json()["followed"] is True

    detail = await client.get(f"/api/topics/{topic_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["followers_count"] == 1
    assert detail.json()["followed_by_user"] is True
