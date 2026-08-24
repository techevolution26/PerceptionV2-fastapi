# tests/test_perceptions.py
import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, name="Ada", email="ada@example.com"):
    res = await client.post(
        "/api/register",
        json={"name": name, "email": email, "password": "supersecret1", "password_confirmation": "supersecret1"},
    )
    body = res.json()
    return body["token"], body["user"]["id"]


async def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


async def _create_topic(db_session):
    from app.models.models import Topic

    async with db_session() as session:
        topic = Topic(name="Technology", description="Tech stuff")
        session.add(topic)
        await session.commit()
        await session.refresh(topic)
        return topic.id


async def test_create_and_list_perception(client, db_session):
    token, _ = await _register(client)
    topic_id = await _create_topic(db_session)

    res = await client.post(
        "/api/perceptions",
        data={"body": "Hello world", "topic_id": str(topic_id)},
        headers=await _auth_headers(token),
    )
    assert res.status_code == 201
    perception = res.json()
    assert perception["body"] == "Hello world"
    assert perception["likes_count"] == 0
    assert perception["liked_by_user"] is False

    res = await client.get("/api/perceptions", headers=await _auth_headers(token))
    assert res.status_code == 200
    assert len(res.json()) == 1


async def test_liked_by_user_reflects_viewer_state(client, db_session):
    """Regression test for the bug found in the original Laravel API: the
    feed never told the frontend whether the *current viewer* had liked a
    perception, so hearts always rendered unfilled on load."""
    token, _ = await _register(client)
    topic_id = await _create_topic(db_session)

    create_res = await client.post(
        "/api/perceptions",
        data={"body": "Liked?", "topic_id": str(topic_id)},
        headers=await _auth_headers(token),
    )
    perception_id = create_res.json()["id"]

    like_res = await client.post(
        f"/api/perceptions/{perception_id}/like", headers=await _auth_headers(token)
    )
    assert like_res.status_code == 200
    assert like_res.json() == {"liked": True, "likes_count": 1}

    list_res = await client.get("/api/perceptions", headers=await _auth_headers(token))
    fetched = list_res.json()[0]
    assert fetched["liked_by_user"] is True
    assert fetched["likes_count"] == 1

    unlike_res = await client.delete(
        f"/api/perceptions/{perception_id}/like", headers=await _auth_headers(token)
    )
    assert unlike_res.json() == {"liked": False, "likes_count": 0}


async def test_cannot_delete_others_perception(client, db_session):
    token_a, _ = await _register(client, "Ada", "ada@example.com")
    token_b, _ = await _register(client, "Bob", "bob@example.com")
    topic_id = await _create_topic(db_session)

    create_res = await client.post(
        "/api/perceptions",
        data={"body": "Mine", "topic_id": str(topic_id)},
        headers=await _auth_headers(token_a),
    )
    perception_id = create_res.json()["id"]

    delete_res = await client.delete(
        f"/api/perceptions/{perception_id}", headers=await _auth_headers(token_b)
    )
    assert delete_res.status_code == 404  # scoped to owner — not visible as "yours" to delete
