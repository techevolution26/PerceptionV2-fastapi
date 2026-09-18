# tests/test_topic_intelligence_route.py
"""Acceptance-level coverage for GET /api/analytics/topics/{topic_id}.

This complements tests/test_topic_intelligence.py, which only exercises the
pure `build_topic_intelligence` function. These tests go through the actual
route, a real (in-memory) database, and the FastAPI auth dependency, per the
Stage 5.1 release principle: "Do not call Stage 5.1 production-ready merely
because the endpoint works."
"""
from datetime import datetime, timezone

import pytest

from app.models.models import (
    Comment,
    CommentIntelligence,
    Perception,
    PerceptionModeration,
    Topic,
    User,
)

pytestmark = pytest.mark.asyncio


async def _register(client, name="Ada", email="ada@example.com"):
    res = await client.post(
        "/api/register",
        json={
            "name": name,
            "email": email,
            "password": "Supersecret1!",
            "password_confirmation": "Supersecret1!",
        },
    )
    body = res.json()
    return body["token"], body["user"]["id"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


async def _seed_qualifying_topic(db_session, *, moderate_second_perception=False):
    """Two Perceptions, five analyzed+distinct-author comments each.

    This is the minimum shape that should qualify for Topic-wide semantic
    conclusions (>=2 qualifying Perceptions, >=5 analyzed comments each,
    >=5 unique participants). When `moderate_second_perception` is True, the
    second Perception is marked as removed and its comments must NOT count.
    """
    async with db_session() as session:
        author = User(name="Author", email="author@example.com", password_hash="x")
        session.add(author)
        await session.flush()

        topic = Topic(name="Technology", description="Tech stuff")
        session.add(topic)
        await session.flush()

        perception_a = Perception(user_id=author.id, topic_id=topic.id, body="A")
        perception_b = Perception(user_id=author.id, topic_id=topic.id, body="B")
        session.add_all([perception_a, perception_b])
        await session.flush()

        if moderate_second_perception:
            session.add(
                PerceptionModeration(perception_id=perception_b.id, status="removed")
            )

        now = datetime.now(timezone.utc)
        for perception in (perception_a, perception_b):
            for i in range(5):
                commenter = User(
                    name=f"Commenter {perception.id}-{i}",
                    email=f"commenter{perception.id}-{i}@example.com",
                    password_hash="x",
                )
                session.add(commenter)
                await session.flush()

                comment = Comment(
                    perception_id=perception.id, user_id=commenter.id, body="c"
                )
                session.add(comment)
                await session.flush()

                session.add(
                    CommentIntelligence(
                        comment_id=comment.id,
                        status="analyzed",
                        sentiment="positive",
                        stance="supportive",
                        themes=["cost"],
                        quality_score=0.9,
                        model_version="test-v1",
                        analyzed_at=now,
                    )
                )
        await session.commit()
        return topic.id


async def test_topic_intelligence_requires_authentication(client, db_session):
    topic_id = await _seed_qualifying_topic(db_session)
    res = await client.get(f"/api/analytics/topics/{topic_id}")
    assert res.status_code == 401


async def test_topic_intelligence_404s_for_missing_topic(client, db_session):
    token, _ = await _register(client)
    res = await client.get(
        "/api/analytics/topics/999999", headers=_auth_headers(token)
    )
    assert res.status_code == 404


async def test_topic_intelligence_qualifies_with_two_clean_perceptions(
    client, db_session
):
    token, _ = await _register(client)
    topic_id = await _seed_qualifying_topic(db_session)

    res = await client.get(
        f"/api/analytics/topics/{topic_id}", headers=_auth_headers(token)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["measurements"]["qualifying_perceptions"]["value"] == 2
    # New governance fields must be present and populated (Drift fix).
    assert body["freshness"]["status"] in ("current", "pending", "stale")
    assert body["quality"]["analyzed_comment_count"] == 10
    assert body["evidence_governance"]["analyzed_comment_count"] == 10
    assert body["semantic_model_governance"]["active_model_versions"]


async def test_topic_intelligence_excludes_moderated_perception(client, db_session):
    """Drift fix regression test: a removed Perception's comments must not
    count toward Topic evidence, matching the moderation filter already
    applied by perceptions/personalization/recommendations/related_creators.
    """
    token, _ = await _register(client)
    topic_id = await _seed_qualifying_topic(
        db_session, moderate_second_perception=True
    )

    res = await client.get(
        f"/api/analytics/topics/{topic_id}", headers=_auth_headers(token)
    )
    assert res.status_code == 200
    body = res.json()
    # Only perception_a should count -> breadth requirement (2) fails.
    assert body["measurements"]["perceptions"]["value"] == 1
    assert body["measurements"]["qualifying_perceptions"]["value"] == 1
    assert body["semantic"]["status"] == "insufficient_breadth"
    assert body["quality"]["analyzed_comment_count"] == 5
