# tests/test_conversations.py
"""
`GET /api/conversations` uses a raw `DISTINCT ON` query (Postgres-only
syntax) to get the most recent message per peer efficiently — see
app/api/routes/conversations.py. SQLite (used by the rest of this suite for
speed) doesn't support it, so that specific endpoint isn't covered by the
fast unit tests here.

To exercise it, run the equivalent of:

    docker compose up -d postgres
    DATABASE_URL=postgresql+asyncpg://perception:perception@localhost:5432/perception \
        pytest tests/test_conversations.py --run-postgres

The send/receive path itself (POST /api/conversations/{peer_id} and
GET /api/conversations/{peer_id}) IS plain portable SQL and is covered below.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, name, email):
    res = await client.post(
        "/api/register",
        json={"name": name, "email": email, "password": "supersecret1", "password_confirmation": "supersecret1"},
    )
    body = res.json()
    return body["token"], body["user"]["id"]


async def test_send_and_fetch_message(client):
    token_a, id_a = await _register(client, "Ada", "ada@example.com")
    _, id_b = await _register(client, "Bob", "bob@example.com")
    headers = {"Authorization": f"Bearer {token_a}"}

    res = await client.post(f"/api/conversations/{id_b}", json={"body": "hi bob"}, headers=headers)
    assert res.status_code == 201
    assert res.json()["body"] == "hi bob"

    res = await client.get(f"/api/conversations/{id_b}", headers=headers)
    assert res.status_code == 200
    messages = res.json()
    assert len(messages) == 1
    assert messages[0]["from_user_id"] == id_a
    assert messages[0]["to_user_id"] == id_b
