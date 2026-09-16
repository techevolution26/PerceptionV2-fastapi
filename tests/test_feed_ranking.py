from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.models import Perception
from app.services.personalization import PersonalizationProfile, score_perception


def profile(**overrides):
    values = dict(
        followed_topic_ids=frozenset(),
        followed_user_ids=frozenset(),
        interacted_topic_scores={},
        role=None,
        industry=None,
        country_code=None,
        region=None,
    )
    values.update(overrides)
    return PersonalizationProfile(**values)


def perception(*, topic_id=1, user_id=2, author=None):
    item = Perception(id=1, topic_id=topic_id, user_id=user_id, body="test")
    item.created_at = datetime.now(timezone.utc)
    item.user = author or SimpleNamespace(
        primary_professional_role=None,
        primary_professional_industry=None,
        location_visibility="private",
        country_code=None,
        region=None,
    )
    return item


def test_followed_creator_beats_same_freshness_unrelated_creator():
    followed = perception(user_id=9)
    unrelated = perception(user_id=10)
    now = followed.created_at
    assert score_perception(followed, profile(followed_user_ids=frozenset({9})), now) > score_perception(
        unrelated, profile(followed_user_ids=frozenset({9})), now
    )


def test_role_and_industry_are_context_signals_not_popularity():
    author = SimpleNamespace(
        primary_professional_role="teacher",
        primary_professional_industry="education",
        location_visibility="private",
        country_code=None,
        region=None,
    )
    item = perception(author=author)
    now = item.created_at
    score = score_perception(item, profile(role="teacher", industry="education"), now)
    assert score == 7.0  # freshness 2 + role 3 + industry 2


def test_private_location_never_contributes_to_feed_score():
    author = SimpleNamespace(
        primary_professional_role=None,
        primary_professional_industry=None,
        location_visibility="private",
        country_code="KE",
        region="Coast",
    )
    item = perception(author=author)
    assert score_perception(item, profile(country_code="KE", region="Coast"), item.created_at) == 2.0
