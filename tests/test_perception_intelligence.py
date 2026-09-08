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
