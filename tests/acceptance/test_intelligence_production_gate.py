import os

import pytest

from .conftest import ANALYTICS_EMAIL, ANALYTICS_PASSWORD, Actor, auth

pytestmark = pytest.mark.acceptance


INTELLIGENCE_REQUIRED_KEYS = {
    "context",
    "provenance",
    "freshness",
    "quality",
    "evidence_governance",
    "semantic_model_governance",
    "measurements",
    "audience",
    "semantic",
    "perspectives",
    "cross_lens_analysis",
    "temporal",
    "patterns",
    "signals",
    "decision_context",
    "methodology",
}


def _configured_perception_id() -> int | None:
    raw = os.getenv("ACCEPTANCE_INTELLIGENCE_PERCEPTION_ID", "").strip()
    return int(raw) if raw else None


def _configured_comparison_ids() -> list[int]:
    raw = os.getenv("ACCEPTANCE_COMPARATIVE_PERCEPTION_IDS", "").strip()
    if not raw:
        return []
    return [int(value.strip()) for value in raw.split(",") if value.strip()]


@pytest.fixture(scope="session")
def analytics_owner(bootstrap_api) -> Actor:
    if not ANALYTICS_EMAIL or not ANALYTICS_PASSWORD:
        pytest.fail(
            "Production intelligence gate requires ACCEPTANCE_ANALYTICS_EMAIL "
            "and ACCEPTANCE_ANALYTICS_PASSWORD."
        )
    response = bootstrap_api.post(
        "/api/login",
        json={"email": ANALYTICS_EMAIL, "password": ANALYTICS_PASSWORD},
    )
    if not response.is_success:
        pytest.fail(
            f"Analytics owner login failed: HTTP {response.status_code} {response.text[:1000]}"
        )
    body = response.json()
    user = body["user"]
    return Actor(
        name=user["name"],
        email=user["email"],
        password=ANALYTICS_PASSWORD,
        token=body["token"],
        user_id=int(user["id"]),
    )


@pytest.mark.asyncio
async def test_perception_intelligence_contract_is_production_complete(
    api, analytics_owner
):
    perception_id = _configured_perception_id()
    if perception_id is None:
        pytest.fail(
            "Set ACCEPTANCE_INTELLIGENCE_PERCEPTION_ID for the production intelligence gate."
        )

    response = await api.get(
        f"/api/analytics/perceptions/{perception_id}",
        headers=auth(analytics_owner),
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) >= INTELLIGENCE_REQUIRED_KEYS

    context = body["context"]
    assert context["schema_version"]
    assert context["perception_id"] == perception_id
    assert context["scope"] in {"creator_analytics", "conversation_intelligence"}
    assert context["viewer_lens"] == "author"
    assert context["access_tier"] == "full"

    assert body["provenance"]["sample_size"] >= 0
    assert body["freshness"]["status"] in {"current", "pending", "stale"}
    assert body["evidence_governance"]["minimum_sample"] == 5
    assert body["methodology"]["sample_minimum"] == 5


@pytest.mark.asyncio
async def test_observer_gets_conversation_intelligence_without_creator_metrics(
    api, actors
):
    perception_id = _configured_perception_id()
    if perception_id is None:
        pytest.fail(
            "Set ACCEPTANCE_INTELLIGENCE_PERCEPTION_ID for the production intelligence gate."
        )

    response = await api.get(
        f"/api/analytics/perceptions/{perception_id}",
        headers=auth(actors["bob"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["context"]["viewer_lens"] == "observer"
    assert body["context"]["scope"] == "conversation_intelligence"
    assert body["measurements"]["views"]["value"] is None
    assert body["measurements"]["shares"]["value"] is None
    assert body["measurements"]["engagement_rate"]["value"] is None
    assert body["measurements"]["daily_activity"] == []


@pytest.mark.asyncio
async def test_free_intelligence_is_a_bounded_teaser(api, actors):
    perception_id = _configured_perception_id()
    if perception_id is None:
        pytest.fail(
            "Set ACCEPTANCE_INTELLIGENCE_PERCEPTION_ID for the production intelligence gate."
        )

    response = await api.get(
        f"/api/analytics/perceptions/{perception_id}",
        headers=auth(actors["charlie"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["context"]["access_tier"] == "free_teaser"
    assert body["context"]["upgrade_available"] is True
    assert body["context"]["upgrade_message"]
    assert len(body["patterns"]) <= 1
    assert len(body["signals"]) <= 1
    assert body["perspectives"]["professional"] == []
    assert body["perspectives"]["geographic"] == []
    assert body["perspectives"]["cross_lens"] == []
    assert body["temporal"]["buckets"] == []
    assert body["temporal"]["changes"] == []


@pytest.mark.asyncio
async def test_ai_status_is_owner_subscription_only(
    api, analytics_owner, actors, topic_id
):
    response = await api.post(
        "/api/perceptions",
        data={"body": "Production gate AI visibility", "topic_id": str(topic_id)},
        headers=auth(analytics_owner),
    )
    assert response.status_code in {200, 201}
    perception_id = int(response.json()["id"])

    comment = await api.post(
        f"/api/perceptions/{perception_id}/comments",
        data={"body": "Pending AI visibility check"},
        headers=auth(actors["bob"]),
    )
    assert comment.status_code == 201
    comment_id = int(comment.json()["id"])

    owner_comments = await api.get(
        f"/api/perceptions/{perception_id}/comments",
        headers=auth(analytics_owner),
    )
    assert owner_comments.status_code == 200
    owner_comment = next(
        item for item in owner_comments.json() if item["id"] == comment_id
    )
    assert owner_comment["ai_analysis_status"] in {"pending", "analyzed", "failed"}

    observer_comments = await api.get(
        f"/api/perceptions/{perception_id}/comments",
        headers=auth(actors["charlie"]),
    )
    assert observer_comments.status_code == 200
    observer_comment = next(
        item for item in observer_comments.json() if item["id"] == comment_id
    )
    assert observer_comment["ai_analysis_status"] is None


@pytest.mark.asyncio
async def test_profile_and_comparative_intelligence_require_analytics_entitlement(
    api, analytics_owner
):
    profile = await api.get(
        "/api/analytics/profile?days=30", headers=auth(analytics_owner)
    )
    assert profile.status_code == 200
    assert profile.json()["sample_minimum"] == 5

    comparison_ids = _configured_comparison_ids()
    if len(comparison_ids) < 2:
        pytest.skip(
            "Set ACCEPTANCE_COMPARATIVE_PERCEPTION_IDS to exercise comparative intelligence."
        )
    comparison = await api.get(
        "/api/analytics/compare",
        params=[("perception_ids", value) for value in comparison_ids[:5]],
        headers=auth(analytics_owner),
    )
    assert comparison.status_code == 200
    body = comparison.json()
    assert body["sample_minimum"] == 5
    assert len(body["perceptions"]) == len(comparison_ids[:5])
