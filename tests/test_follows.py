# tests/test_follows.py
import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, name, email):
    res = await client.post(
        "/api/register",
        json={"name": name, "email": email, "password": "supersecret1", "password_confirmation": "supersecret1"},
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
