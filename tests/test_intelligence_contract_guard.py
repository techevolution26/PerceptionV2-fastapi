from app.services.intelligence_contract_guard import validate_perception_intelligence


def base_payload():
    return {
        "context": {
            "scope": "conversation_intelligence",
            "viewer_lens": "observer",
        },
        "measurements": {
            "views": {"value": None, "available": False},
            "shares": {"value": None, "available": False},
            "engagement_rate": {"value": None, "available": False},
            "daily_activity": [],
        },
        "semantic": {
            "status": "insufficient_sample",
            "sample_minimum": 5,
            "analyzed_comment_count": 0,
            "sentiment_distribution": [],
            "stance_distribution": [],
            "top_themes": [],
            "concern_themes": [],
            "agreement_themes": [],
            "disagreement_themes": [],
        },
        "audience": {
            "unique_participants": 0,
            "breakdown": {
                "minimum": 5,
                "available": False,
                "countries": [],
                "regions": [],
                "professional_roles": [],
                "verified_professional_roles": [],
            },
        },
        "decision_context": {"evidence_invariant": True},
    }


def test_zero_comment_observer_payload_is_valid():
    assert validate_perception_intelligence(base_payload()) == []


def test_observer_cannot_expose_creator_metrics():
    payload = base_payload()
    payload["measurements"]["views"] = {"value": 9, "available": True}
    errors = validate_perception_intelligence(payload)
    assert any("views" in error for error in errors)


def test_insufficient_semantic_sample_cannot_have_distribution():
    payload = base_payload()
    payload["semantic"]["sentiment_distribution"] = [
        {"label": "positive", "comments": 4, "share": 1.0}
    ]
    errors = validate_perception_intelligence(payload)
    assert any("sentiment_distribution" in error for error in errors)


def test_audience_breakdown_requires_minimum():
    payload = base_payload()
    payload["audience"]["unique_participants"] = 4
    payload["audience"]["breakdown"]["available"] = True
    errors = validate_perception_intelligence(payload)
    assert any("audience breakdown" in error for error in errors)


def test_decision_context_must_preserve_evidence_invariance():
    payload = base_payload()
    payload["decision_context"]["evidence_invariant"] = False
    errors = validate_perception_intelligence(payload)
    assert any("evidence_invariant" in error for error in errors)
