from app.services.related_creators import (
    CANDIDATE_LIMIT,
    MIN_SEMANTIC_PARTICIPANTS,
    MIN_SEMANTIC_SAMPLE,
)


def test_related_creator_semantic_thresholds_are_bounded():
    assert MIN_SEMANTIC_SAMPLE == 5
    assert MIN_SEMANTIC_PARTICIPANTS == 5
    assert CANDIDATE_LIMIT == 150
