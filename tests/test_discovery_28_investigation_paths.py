from pathlib import Path

from app.services.investigation_paths import build_investigation_paths


def test_discovery_28_docs_exist() -> None:
    assert Path("DISCOVERY_28_INVESTIGATION_PATHS.md").exists()


def test_paths_are_questions_not_decisions() -> None:
    paths = build_investigation_paths(
        intent="research",
        observations=[{
            "title": "Recurring theme",
            "description": "People repeatedly mention access to training.",
            "evidence_source": "top_themes",
            "sample_size": 7,
        }],
    )
    assert paths
    assert "confirm" in paths[0]["question"] or "evidence" in paths[0]["question"]
    assert "independent" in paths[0]["validation_step"]


def test_insufficient_observations_produce_no_paths() -> None:
    assert build_investigation_paths(
        intent="business",
        observations=[{"title": "Pattern", "description": "x", "sample_size": 4}],
    ) == []
