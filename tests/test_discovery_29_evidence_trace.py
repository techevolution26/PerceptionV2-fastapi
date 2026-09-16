from pathlib import Path

from app.services.investigation_paths import build_investigation_paths


def test_discovery_29_docs_exist() -> None:
    assert Path("DISCOVERY_29_EVIDENCE_TRACE.md").exists()


def test_evidence_trace_contract_terms_are_documented() -> None:
    text = Path("DISCOVERY_29_EVIDENCE_TRACE.md").read_text()
    for term in ("trace identifier", "sample size", "analysis period", "limitations"):
        assert term in text


def test_investigation_paths_remain_validation_oriented() -> None:
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
    assert "independent" in paths[0]["validation_step"]
