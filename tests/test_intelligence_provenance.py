from datetime import datetime, timezone

from app.services.perception_intelligence import orchestrate_perception_intelligence


def test_provenance_is_attached_to_root_patterns_and_signals():
    now = datetime.now(timezone.utc)
    rows = []
    result = orchestrate_perception_intelligence(
        topic_id=1,
        topic_name="Technology",
        perception_id=1,
        period_start=now,
        period_end=now,
        period_days=30,
        semantic_rows=rows,
        participant_rows=[],
        cross_lens={},
        scope="conversation_intelligence",
        viewer_lens="observer",
    )
    assert result["provenance"]["sample_size"] == 0
    assert result["provenance"]["scope"] == "conversation_intelligence"
    assert result["patterns"] == []
    assert result["signals"] == []
