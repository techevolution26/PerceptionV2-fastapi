from datetime import datetime, timezone

from app.models.models import CommentIntelligence
from app.services.comment_intelligence import aggregate_comment_intelligence


def _row(**kwargs):
    row = CommentIntelligence(
        comment_id=kwargs.pop("comment_id", 1),
        status="analyzed",
        themes=kwargs.pop("themes", []),
        is_question=kwargs.pop("is_question", False),
        has_concern=kwargs.pop("has_concern", False),
        agreement_signal=kwargs.pop("agreement_signal", False),
        disagreement_signal=kwargs.pop("disagreement_signal", False),
        analyzed_at=datetime.now(timezone.utc),
        **kwargs,
    )
    return row


def test_semantic_aggregate_suppresses_small_samples():
    result = aggregate_comment_intelligence(
        [_row(comment_id=i, sentiment="positive") for i in range(4)],
        period_days=30,
    )
    assert result["semantic_analysis_status"] == "insufficient_sample"
    assert result["analyzed_comment_count"] == 4
    assert result["sentiment_distribution"] == []


def test_semantic_aggregate_preserves_evidence_metadata():
    rows = [
        _row(comment_id=1, sentiment="positive", stance="supportive", themes=["training"], quality_score=0.8, agreement_signal=True),
        _row(comment_id=2, sentiment="positive", stance="supportive", themes=["training"], quality_score=0.9, agreement_signal=True),
        _row(comment_id=3, sentiment="neutral", stance="unclear", themes=["cost"], quality_score=0.7, is_question=True),
        _row(comment_id=4, sentiment="negative", stance="challenging", themes=["cost"], quality_score=0.6, has_concern=True, disagreement_signal=True),
        _row(comment_id=5, sentiment="mixed", stance="mixed", themes=["training", "cost"], quality_score=0.8, has_concern=True),
    ]
    result = aggregate_comment_intelligence(rows, period_days=30)

    assert result["semantic_analysis_status"] == "available"
    assert result["analyzed_comment_count"] == 5
    assert result["semantic_quality_score"] == 0.76
    assert result["question_count"] == 1
    assert result["sentiment_distribution"][0]["label"] == "positive"
    assert result["top_themes"][0]["theme"] == "training"
