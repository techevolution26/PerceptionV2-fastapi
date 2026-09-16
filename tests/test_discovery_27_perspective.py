from pathlib import Path

from app.services.decision_intelligence import build_decision_intelligence


SUPPORTED = [
    "general_exploration",
    "research",
    "business",
    "policy",
    "journalism",
    "education",
    "product",
    "professional",
]


def test_discovery_27_docs_exist() -> None:
    assert Path("DISCOVERY_27_PERSPECTIVE_DECISION_CONTEXT.md").exists()


def test_decision_context_preserves_evidence() -> None:
    signals = [
        {
            "label": "Recurring theme",
            "description": "A recurring observed theme.",
            "sample_size": 5,
        }
    ]
    for intent in SUPPORTED:
        result = build_decision_intelligence(
            intent=intent,
            patterns=[],
            signals=signals,
            cross_lens_analysis={},
            minimum=5,
        )
        assert result["evidence_invariant"] is True
        assert result["observations"][0]["sample_size"] == 5
        assert result["observations"][0]["description"] == "A recurring observed theme."
