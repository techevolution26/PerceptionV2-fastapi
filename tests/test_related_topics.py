from app.services.related_topics import MIN_SEMANTIC_PARTICIPANTS, MIN_SEMANTIC_SAMPLE


def test_related_topic_semantic_thresholds_are_bounded():
    assert MIN_SEMANTIC_SAMPLE == 5
    assert MIN_SEMANTIC_PARTICIPANTS == 5
