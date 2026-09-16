from app.services.perception_moderation import assess_perception


def test_normal_perception_is_published():
    result = assess_perception("Public transport improves access to work and education.")
    assert result.status == "published"
    assert result.flags == []


def test_multiple_independent_spam_privacy_signals_require_review():
    result = assess_perception(
        "BUY NOW BUY NOW BUY NOW BUY NOW BUY NOW "
        "https://example.com https://example.org "
        "contact me at 0712345678"
    )
    assert result.status == "pending_review"
    assert "link_heavy" in result.flags
    assert "contact_information" in result.flags


def test_single_observable_signal_does_not_hold_a_perception():
    result = assess_perception("Read more at https://example.com")
    assert result.status == "published"
    assert result.flags == ["link_heavy"]


def test_contact_information_is_flagged_without_judging_the_viewpoint():
    result = assess_perception("For project details contact me at test@example.com")
    assert result.status == "published"
    assert "contact_information" in result.flags
