from datetime import datetime, timedelta, timezone

from app.models.models import CommentIntelligence
from app.services.temporal_intelligence import build_temporal_intelligence


def _row(stake: str, theme: str) -> CommentIntelligence:
    row = CommentIntelligence(comment_id=1)
    row.status = "analyzed"
    row.sentiment = "positive"
    row.stance = stake
    row.themes = [theme]
    row.is_question = False
    row.has_concern = False
    row.agreement_signal = True
    row.disagreement_signal = False
    row.quality_score = 0.9
    return row


def test_temporal_suppresses_small_windows_and_uses_qualifying_changes():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(5):
        rows.append((_row("supports", "cost"), start + timedelta(days=i)))
    for i in range(5):
        rows.append((_row("challenges", "access"), start + timedelta(days=7+i)))
    result = build_temporal_intelligence(rows, period_start=start, period_end=start + timedelta(days=14))
    assert result["status"] == "available"
    assert result["qualifying_bucket_count"] == 2
    assert result["changes"][0]["stance_changed"] is True
    assert result["changes"][0]["theme_changed"] is True
