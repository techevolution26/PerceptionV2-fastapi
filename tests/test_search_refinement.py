import pytest

pytestmark = pytest.mark.asyncio


async def _register(client, name, email):
    response = await client.post(
        "/api/register",
        json={
            "name": name,
            "email": email,
            "password": "Supersecret1!",
            "password_confirmation": "Supersecret1!",
        },
    )
    body = response.json()
    return body["token"], body["user"]["id"]


async def _topic(db_session, name):
    from app.models.models import Topic

    async with db_session() as session:
        topic = Topic(name=name, description=name)
        session.add(topic)
        await session.commit()
        await session.refresh(topic)
        return topic.id


async def _perception(client, token, topic_id, body):
    response = await client.post(
        "/api/perceptions",
        data={"body": body, "topic_id": str(topic_id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def test_search_supports_recent_sort_and_topic_filter(client, db_session):
    token, _ = await _register(client, "Ada", "ada-search@example.com")
    climate_id = await _topic(db_session, "Climate")
    tech_id = await _topic(db_session, "Technology")

    await _perception(client, token, climate_id, "Climate resilience in coastal communities")
    await _perception(client, token, tech_id, "Climate data tools for schools")

    response = await client.get(
        f"/api/search?query=climate&topic_id={climate_id}&sort=recent",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["topic"]["id"] == climate_id
    assert "Climate resilience" in results[0]["body"]


async def test_search_relevance_does_not_use_engagement_counts(client, db_session):
    token_a, id_a = await _register(client, "Ada", "ada-relevance@example.com")
    token_b, id_b = await _register(client, "Bob", "bob-relevance@example.com")
    topic_id = await _topic(db_session, "Education")

    first = await _perception(client, token_a, topic_id, "Education technology and classrooms")
    second = await _perception(client, token_b, topic_id, "Education policy and teachers")

    # Add engagement to the second perception. Search ranking must remain a
    # textual/contextual relevance decision, not a popularity score.
    for _ in range(2):
        await client.post(f"/api/perceptions/{second}/like", headers={"Authorization": f"Bearer {token_a}"})

    response = await client.get(
        "/api/search?query=technology",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200
    results = response.json()
    assert results[0]["id"] == first
    assert all(item["id"] != second or item["body"].startswith("Education") for item in results)
