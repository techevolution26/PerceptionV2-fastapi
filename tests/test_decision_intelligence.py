from app.services.decision_intelligence import build_decision_intelligence


def test_decision_intelligence_is_insufficient_without_qualified_evidence():
    result = build_decision_intelligence(
        intent="research",
        patterns=[],
        signals=[],
        cross_lens_analysis={},
    )
    assert result["status"] == "insufficient_sample"
    assert result["observations"] == []
    assert result["evidence_invariant"] is True


def test_decision_intelligence_reframes_without_changing_observations():
    patterns = [
        {
            "label": "Recurring theme",
            "description": "The theme 'cost' occurs in 6 analyzed comments.",
            "evidence_types": ["top_themes"],
        }
    ]
    signals = [
        {
            "label": "Recurring theme",
            "description": "The theme 'cost' occurs in 6 analyzed comments.",
            "sample_size": 6,
            "limitations": ["No causation"],
        }
    ]
    result = build_decision_intelligence(
        intent="business",
        patterns=patterns,
        signals=signals,
        cross_lens_analysis={},
    )
    assert result["status"] == "available"
    assert result["observations"][0]["description"] == patterns[0]["description"]
    assert result["evidence_invariant"] is True
    assert "causation" in result["guardrail"].lower()


def test_decision_intents_change_guidance_not_evidence():
    pattern = {
        "label": "Question activity",
        "description": "3 analyzed comments contain a question signal.",
        "evidence_types": ["question_count"],
    }
    signal = {
        "label": pattern["label"],
        "description": pattern["description"],
        "sample_size": 8,
        "limitations": [],
    }
    research = build_decision_intelligence(
        intent="research", patterns=[pattern], signals=[signal], cross_lens_analysis={}
    )
    education = build_decision_intelligence(
        intent="education", patterns=[pattern], signals=[signal], cross_lens_analysis={}
    )
    assert research["observations"] == education["observations"]
    assert research["considerations"] != education["considerations"]
