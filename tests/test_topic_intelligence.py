from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.topic_intelligence import build_topic_intelligence


def _row(
    comment_id: int, perception_id: int, created_at: datetime, theme: str = "theme"
):
    return SimpleNamespace(
        id=comment_id,
        comment_id=comment_id,
        status="analyzed",
        sentiment="positive",
        stance="supportive",
        themes=[theme],
        is_question=False,
        has_concern=False,
        agreement_signal=True,
        disagreement_signal=False,
        quality_score=0.9,
        model_version="test",
        analyzed_at=created_at,
    )


def test_topic_intelligence_requires_two_qualifying_perceptions():
    now = datetime.now(timezone.utc)
    rows = [(_row(i, 1, now), 1, now) for i in range(5)]
    users = [
        (
            rows[i][0],
            SimpleNamespace(
                id=i + 1,
                primary_professional_role=None,
                profession=None,
                country_code="KE",
                region="Coast",
            ),
        )
        for i in range(5)
    ]
    result = build_topic_intelligence(
        topic_id=1,
        topic_name="Technology",
        semantic_rows=rows,
        participant_rows=users,
        period_start=now,
        period_end=now,
        access_tier="full",
        upgrade_available=False,
        upgrade_message=None,
    )
    assert result["semantic"]["status"] == "insufficient_breadth"
    assert result["patterns"] == []


def test_topic_intelligence_qualifies_across_two_perceptions():
    now = datetime.now(timezone.utc)
    rows = [(_row(i, 1, now), 1, now) for i in range(5)] + [
        (_row(i + 5, 2, now), 2, now) for i in range(5)
    ]
    users = [
        (
            row[0],
            SimpleNamespace(
                id=i + 1,
                primary_professional_role=None,
                profession=None,
                country_code="KE",
                region="Coast",
            ),
        )
        for i, row in enumerate(rows)
    ]
    result = build_topic_intelligence(
        topic_id=1,
        topic_name="Technology",
        semantic_rows=rows,
        participant_rows=users,
        period_start=now,
        period_end=now,
        access_tier="full",
        upgrade_available=False,
        upgrade_message=None,
    )
    assert result["semantic"]["status"] == "available"
    assert result["measurements"]["qualifying_perceptions"]["value"] == 2
    assert result["provenance"]["source"] == "topic_intelligence"


def test_topic_free_teaser_is_bounded():
    now = datetime.now(timezone.utc)
    rows = [(_row(i, 1, now), 1, now) for i in range(5)] + [
        (_row(i + 5, 2, now), 2, now) for i in range(5)
    ]
    users = [
        (
            row[0],
            SimpleNamespace(
                id=i + 1,
                primary_professional_role=None,
                profession=None,
                country_code="KE",
                region="Coast",
            ),
        )
        for i, row in enumerate(rows)
    ]
    result = build_topic_intelligence(
        topic_id=1,
        topic_name="Technology",
        semantic_rows=rows,
        participant_rows=users,
        period_start=now,
        period_end=now,
        access_tier="free_teaser",
        upgrade_available=True,
        upgrade_message="Subscribe",
    )
    assert result["context"]["access_tier"] == "free_teaser"
    assert result["perspectives"]["professional"] == []
    assert result["temporal"]["buckets"] == []
    assert len(result["patterns"]) <= 1


def test_topic_intelligence_withholds_semantics_for_low_participant_count():
    now = datetime.now(timezone.utc)
    rows = [(_row(i, 1, now), 1, now) for i in range(5)] + [
        (_row(i + 5, 2, now), 2, now) for i in range(5)
    ]
    users = [
        (
            row[0],
            SimpleNamespace(
                id=1,
                primary_professional_role=None,
                profession=None,
                country_code="KE",
                region="Coast",
            ),
        )
        for row in rows
    ]
    result = build_topic_intelligence(
        topic_id=1,
        topic_name="Technology",
        semantic_rows=rows,
        participant_rows=users,
        period_start=now,
        period_end=now,
        access_tier="full",
        upgrade_available=False,
        upgrade_message=None,
    )
    assert result["semantic"]["status"] == "insufficient_participants"
    assert result["semantic"]["sentiment_distribution"] == []
    assert result["semantic"]["stance_distribution"] == []
    assert result["patterns"] == []
    assert result["measurements"]["unique_participants"]["value"] is None
    assert result["measurements"]["unique_participants"]["available"] is False


def test_topic_intelligence_exposes_semantics_at_participant_threshold():
    now = datetime.now(timezone.utc)
    rows = [(_row(i, 1, now), 1, now) for i in range(5)] + [
        (_row(i + 5, 2, now), 2, now) for i in range(5)
    ]
    users = [
        (
            row[0],
            SimpleNamespace(
                id=i + 1,
                primary_professional_role=None,
                profession=None,
                country_code="KE",
                region="Coast",
            ),
        )
        for i, row in enumerate(rows)
    ]
    result = build_topic_intelligence(
        topic_id=1,
        topic_name="Technology",
        semantic_rows=rows,
        participant_rows=users,
        period_start=now,
        period_end=now,
        access_tier="full",
        upgrade_available=False,
        upgrade_message=None,
    )
    assert result["semantic"]["status"] == "available"
    assert result["semantic"]["participant_minimum"] == 5
    assert result["measurements"]["unique_participants"]["value"] == 10
