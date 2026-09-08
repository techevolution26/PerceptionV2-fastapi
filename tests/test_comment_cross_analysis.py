from types import SimpleNamespace

from app.services.comment_cross_analysis import (
    aggregate_professional_geographic_semantics,
)


def _row(i: int, *, role: str = "software_engineer", country: str = "KE", region: str = "Coast"):
    intelligence = SimpleNamespace(
        sentiment="positive" if i % 2 else "neutral",
        stance="supportive",
        themes=["access"],
        is_question=i % 3 == 0,
        quality_score=0.9,
    )
    user = SimpleNamespace(
        primary_professional_role=role,
        profession=None,
        country_code=country,
        region=region,
    )
    return intelligence, user


def test_cross_analysis_suppresses_small_samples():
    result = aggregate_professional_geographic_semantics([_row(i) for i in range(4)])
    assert result["cross_analysis_status"] == "insufficient_sample"
    assert result["professional_semantic_segments"] == []


def test_cross_analysis_reports_qualifying_cohorts():
    rows = [_row(i) for i in range(5)]
    result = aggregate_professional_geographic_semantics(rows)
    assert result["cross_analysis_status"] == "available"
    assert result["professional_semantic_segments"][0]["sample_size"] == 5
    assert result["professional_geographic_segments"][0]["geography"] == "KE · Coast"
    assert result["professional_geographic_segments"][0]["role_label"] == "Software Engineer"
    assert result["professional_geographic_segments"][0]["top_themes"][0]["theme"] == "access"
