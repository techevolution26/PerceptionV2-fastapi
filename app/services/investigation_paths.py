"""Deterministic investigation paths derived from qualified observations.

Investigation paths are prompts for further inquiry. They never add evidence,
rank decisions, predict outcomes, or infer participant identity.
"""
from __future__ import annotations

from typing import Any

from app.schemas.investigation_paths import InvestigationPath


def build_investigation_paths(
    *,
    intent: str,
    observations: list[dict[str, Any]],
    minimum: int = 5,
) -> list[dict[str, str]]:
    normalized = intent.strip().lower()
    paths: list[dict[str, str]] = []

    for observation in observations[:4]:
        title = str(observation.get("title", "Observed pattern"))
        description = str(observation.get("description", ""))
        evidence_source = str(observation.get("evidence_source", "observed evidence"))
        sample_size = int(observation.get("sample_size", 0))
        if sample_size < minimum:
            continue

        if "divergence" in title.lower() or "difference" in title.lower():
            path = InvestigationPath(
                title="Investigate the difference",
                question=f"What evidence could explain or test the observed difference in {title.lower()}?",
                rationale="The conversation contains a qualifying difference that is useful as a question for further inquiry, not as an explanation by itself.",
                evidence_basis=f"{evidence_source}; sample {sample_size}.",
                validation_step="Compare the relevant claims or experiences with independent sources and additional perspectives.",
            )
        elif "change" in title.lower() or "temporal" in title.lower():
            path = InvestigationPath(
                title="Investigate the change",
                question="What changed in the surrounding context when this pattern shifted?",
                rationale="A qualifying time-window change can identify a useful investigation lead without establishing why the change occurred.",
                evidence_basis=f"{evidence_source}; sample {sample_size}.",
                validation_step="Check the underlying time windows and seek independent contextual evidence before interpreting the change.",
            )
        else:
            path = InvestigationPath(
                title="Test the recurring pattern",
                question=f"What additional evidence would confirm, refine, or challenge: {description}",
                rationale="A recurring observation is a starting point for verification rather than a conclusion.",
                evidence_basis=f"{evidence_source}; sample {sample_size}.",
                validation_step="Seek independent evidence and deliberately include perspectives that could disagree with the observed pattern.",
            )
        paths.append(path.model_dump())

    if paths and normalized in {"research", "journalism", "policy"}:
        paths.append(
            InvestigationPath(
                title="Check what is missing",
                question="Which relevant perspective or evidence is not represented in this discussion?",
                rationale="A platform conversation can reveal useful signals while still leaving important evidence outside the observed sample.",
                evidence_basis="Conversation-derived evidence only.",
                validation_step="Identify relevant external sources, affected groups, or domain evidence that are absent here.",
            ).model_dump()
        )

    return paths[:3]
