from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models.models import Perception
from app.services.personalization import PersonalizationProfile, score_perception


def _profile(**overrides):
    values = {
        "followed_topic_ids": frozenset(),
        "followed_user_ids": frozenset(),
        "interacted_topic_scores": {},
        "role": None,
        "industry": None,
        "country_code": None,
        "region": None,
    }
    values.update(overrides)
    return PersonalizationProfile(**values)


def _perception(*, topic_id=1, user_id=2, author=None):
    p = Perception(id=1, topic_id=topic_id, user_id=user_id, body="test")
    p.created_at = datetime.now(timezone.utc)
    p.user = author or SimpleNamespace(
        primary_professional_role=None,
        primary_professional_industry=None,
        location_visibility="private",
        country_code=None,
        region=None,
    )
    return p


def test_followed_topic_is_a_strong_personalization_signal():
    p = _perception(topic_id=7)
    followed = score_perception(
        p, _profile(followed_topic_ids=frozenset({7})), p.created_at
    )
    unrelated = score_perception(p, _profile(), p.created_at)
    assert followed > unrelated
    assert followed - unrelated == 6.0


def test_global_popularity_is_not_part_of_personalization_score():
    p = _perception(topic_id=7)
    p.likes_count = 999999
    p.comments_count = 999999
    personalized = score_perception(
        p, _profile(interacted_topic_scores={7: 3}), p.created_at
    )
    baseline = score_perception(p, _profile(), p.created_at)
    assert personalized - baseline == 3.0


def test_private_creator_location_does_not_add_geographic_signal():
    author = SimpleNamespace(
        primary_professional_role=None,
        primary_professional_industry=None,
        location_visibility="private",
        country_code="KE",
        region="Coast",
    )
    p = _perception(author=author)
    score = score_perception(
        p, _profile(country_code="KE", region="Coast"), p.created_at
    )
    assert score == 2.0  # freshness only; no private-location contribution
