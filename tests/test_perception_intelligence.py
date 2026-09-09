from datetime import datetime, timezone

from app.services.perception_intelligence import (
    build_cross_lens_evidence,
    build_evidence_envelope,
    build_semantic_evidence,
    decision_context,
    qualify_signal,
)


def test_evidence_envelope_is_scoped_and_sample_aware():
    envelope = build_evidence_envelope(
        topic_id=7,
        topic_name="Technology",
        perception_id=12,
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
        sample_size=4,
        scope="test",
        evidence=[{"type": "count", "observed": 4}],
    )
    assert envelope["evidence_status"] == "insufficient_sample"
    assert envelope["topic"]["name"] == "Technology"
    assert envelope["sample_size"] == 4


def test_signal_is_not_created_below_minimum():
    evidence = {"sample_size": 4, "limitations": []}
    assert qualify_signal(label="x", description="y", evidence=evidence) is None


def test_decision_context_does_not_mutate_evidence():
    signal = {"label": "Observed", "evidence": {"sample_size": 8}}
    context = decision_context(intent="business", signals=[signal])
    assert context["intent"] == "business"
    assert context["signals"][0] is signal
    assert context["evidence_invariant"] is True


def test_cross_lens_evidence_keeps_cohort_outputs_as_observed_data():
    result = build_cross_lens_evidence(
        topic_id=1,
        topic_name="Agriculture",
        perception_id=2,
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        total_analyzed_comments=9,
        professional_segments=[{"role_label": "Farmer", "sample_size": 5}],
        geographic_segments=[],
        professional_geographic_segments=[],
    )
    assert result["evidence_status"] == "available"
    assert result["evidence"][0]["type"] == "professional_perspectives"


def test_orchestrator_composes_semantic_and_cross_lens_layers():
    from app.services.perception_intelligence import orchestrate_perception_intelligence

    result = orchestrate_perception_intelligence(
        topic_id=4,
        topic_name="Technology",
        perception_id=9,
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
        period_days=31,
        semantic_rows=[],
        participant_rows=[],
        cross_lens={
            "professional_semantic_segments": [],
            "geographic_semantic_segments": [],
            "professional_geographic_segments": [],
        },
    )
    assert result["schema_version"] == "1.0"
    assert result["topic"]["name"] == "Technology"
    assert result["semantic"]["semantic_evidence"]["evidence_status"] == "insufficient_sample"
    assert result["cross_lens"]["evidence_status"] == "insufficient_sample"


def test_derive_patterns_and_signals_is_sample_gated():
    from app.services.perception_intelligence import derive_patterns_and_signals

    insufficient = {
        "sample_size": 4,
        "evidence": [],
        "limitations": ["test limitation"],
    }
    patterns, signals = derive_patterns_and_signals(
        semantic_evidence=insufficient,
        cross_lens_evidence=insufficient,
    )
    assert patterns == []
    assert signals == []


def test_derive_patterns_and_signals_only_emits_descriptive_signals():
    from app.services.perception_intelligence import derive_patterns_and_signals

    semantic = {
        "sample_size": 10,
        "limitations": ["No causation"],
        "evidence": [
            {"type": "sentiment_distribution", "observed": [{"label": "positive", "comments": 6}]},
            {"type": "stance_distribution", "observed": [{"label": "supportive", "comments": 7}]},
            {"type": "top_themes", "observed": [{"theme": "cost", "comments": 5}]},
            {"type": "question_count", "observed": 3},
            {"type": "concern_themes", "observed": [{"theme": "cost", "comments": 4}]},
            {"type": "agreement_themes", "observed": [{"theme": "value", "comments": 3}]},
            {"type": "disagreement_themes", "observed": [{"theme": "cost", "comments": 2}]},
        ],
    }
    cross = {
        "sample_size": 10,
        "limitations": ["No causation"],
        "evidence": [
            {"type": "professional_perspectives", "observed": [{"role_code": "a"}, {"role_code": "b"}]},
            {"type": "geographic_perspectives", "observed": [{"geography": "KE · Coast"}, {"geography": "KE · Nairobi"}]},
            {"type": "professional_geographic_perspectives", "observed": []},
        ],
    }

    patterns, signals = derive_patterns_and_signals(
        semantic_evidence=semantic,
        cross_lens_evidence=cross,
    )

    labels = {item["label"] for item in patterns}
    assert "Dominant sentiment" in labels
    assert "Dominant stance" in labels
    assert "Recurring theme" in labels
    assert "Question activity" in labels
    assert "Concern theme" in labels
    assert "Mixed response signals" in labels
    assert "Multiple qualifying perspectives" in labels
    assert len(signals) == len(patterns)
    assert all(signal["status"] == "observed_signal" for signal in signals)
    assert all(signal["sample_size"] == 10 for signal in signals)
    assert all("causation" in " ".join(signal["limitations"]).lower() for signal in signals)
    assert all("predict" not in signal["description"].lower() for signal in signals)
