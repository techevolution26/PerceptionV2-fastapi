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
