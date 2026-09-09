from datetime import datetime, timezone, timedelta

from app.services.profile_intelligence import build_profile_intelligence


def _row(comment_id: int, perception_id: int, topic: str, when: datetime, theme: str):
    class Row:
        def __init__(self):
            self.id = comment_id
            self.status = "analyzed"
            self.sentiment = "positive"
            self.stance = "supports"
            self.themes = [theme]
            self.is_question = False
            self.has_concern = False
            self.quality_score = 0.9
    return Row(), perception_id, 1 if topic == "Technology" else 2, topic, when


def test_longitudinal_intelligence_requires_minimum_sample():
    class Topic:
        def __init__(self, name): self.name = name
    class Perception:
        def __init__(self, pid, topic_id, topic): self.id = pid; self.topic_id = topic_id; self.topic = topic

    now = datetime.now(timezone.utc)
    perceptions = [Perception(1, 1, Topic("Technology")), Perception(2, 2, Topic("Agriculture"))]
    rows = [_row(i, 1, "Technology", now - timedelta(days=i), "access") for i in range(5)]
    rows += [_row(i + 10, 2, "Agriculture", now - timedelta(days=i), "access") for i in range(5)]
    result = build_profile_intelligence(
        perceptions=perceptions,
        semantic_rows=rows,
        period_start=now - timedelta(days=30),
        period_end=now,
    )
    assert result["analyzed_comment_count"] == 10
    assert len(result["topics"]) == 2
    assert result["recurring_themes"][0]["topic_count"] == 2
