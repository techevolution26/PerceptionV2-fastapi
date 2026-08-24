# tests/test_auth.py
import pytest

pytestmark = pytest.mark.asyncio


async def test_register_and_login(client):
    res = await client.post(
        "/api/register",
        json={
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "password": "supersecret1",
            "password_confirmation": "supersecret1",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == "ada@example.com"
    assert "email" in body["user"]  # /register returns UserMe — includes email
    assert body["token"]

    res = await client.post(
        "/api/login", json={"email": "ada@example.com", "password": "supersecret1"}
    )
    assert res.status_code == 200
    assert res.json()["token"]


async def test_register_password_mismatch_returns_422(client):
    res = await client.post(
        "/api/register",
        json={
            "name": "Bob",
            "email": "bob@example.com",
            "password": "supersecret1",
            "password_confirmation": "different",
        },
    )
    assert res.status_code == 422


async def test_login_wrong_password_returns_422(client):
    await client.post(
        "/api/register",
        json={
            "name": "Carl",
            "email": "carl@example.com",
            "password": "supersecret1",
            "password_confirmation": "supersecret1",
        },
    )
    res = await client.post("/api/login", json={"email": "carl@example.com", "password": "wrongpass"})
    assert res.status_code == 422


async def test_get_me_requires_auth(client):
    res = await client.get("/api/user")
    assert res.status_code == 401


async def test_public_profile_never_includes_email(client):
    register = await client.post(
        "/api/register",
        json={
            "name": "Dana",
            "email": "dana@example.com",
            "password": "supersecret1",
            "password_confirmation": "supersecret1",
        },
    )
    user_id = register.json()["user"]["id"]

    res = await client.get(f"/api/users/{user_id}")
    assert res.status_code == 200
    assert "email" not in res.json()
