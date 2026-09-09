"""Deterministic decision framing for Perception Intelligence.

This service never creates new evidence. It reframes already-qualified
patterns, signals, cross-lens comparisons, and temporal observations for a
selected decision intent.
"""
from __future__ import annotations

from typing import Any

from app.schemas.decision_intelligence import DecisionIntent

MINIMUM_SAMPLE = 5

_INTENT_GUIDANCE: dict[str, tuple[str, str]] = {
    "research": (
        "Research framing",
        "Use observed themes, questions, and differences as hypotheses or areas for further investigation; validate them with appropriate research methods.",
    ),
    "business": (
        "Business framing",
        "Use observed response patterns and recurring concerns as areas for market or customer follow-up; do not treat them as population-wide demand estimates.",
    ),
    "policy": (
        "Policy framing",
        "Use observed concerns, questions, and cross-lens differences as areas for consultation or policy investigation; broader public conclusions require representative evidence.",
    ),
    "journalism": (
        "Journalism framing",
        "Use recurring themes and notable differences as reporting leads; independently verify claims and seek perspectives beyond this observed discussion.",
    ),
    "education": (
        "Education framing",
        "Use recurring questions, concerns, and themes to identify areas where explanation, examples, or additional learning support may be useful.",
    ),
    "product": (
        "Product framing",
        "Use recurring concerns, questions, and response differences as candidate areas for product discovery and validation; they are not automatically feature requirements.",
    ),
    "professional": (
        "Professional framing",
        "Use observed patterns and cross-lens differences as areas for professional reflection or further inquiry without assuming that a cohort represents every member of that profession.",
    ),
    "general_exploration": (
        "Exploration framing",
        "Use the observed patterns and differences as a structured starting point for understanding the discussion and deciding what to investigate next.",
    ),
}


def build_decision_intelligence(
    *,
    intent: str,
    patterns: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    cross_lens_analysis: dict[str, Any],
    temporal: dict[str, Any] | None = None,
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    normalized = intent.strip().lower()
    if normalized not in _INTENT_GUIDANCE:
        raise ValueError(f"Unsupported decision intent: {intent}")

    qualified_samples = [
        int(item.get("sample_size", 0))
        for item in signals
        if int(item.get("sample_size", 0)) >= minimum
    ]
    has_evidence = bool(qualified_samples)
    title, guidance = _INTENT_GUIDANCE[normalized]

    observations: list[dict[str, Any]] = []
    signal_by_label = {str(item.get("label")): item for item in signals}
    for pattern in patterns[:8]:
        matching_signal = signal_by_label.get(str(pattern.get("label")), {})
        sample_size = int(matching_signal.get("sample_size", 0))
        if sample_size < minimum:
            continue
        observations.append(
            {
                "title": str(pattern.get("label", "Observed pattern")),
                "description": str(pattern.get("description", "")),
                "evidence_source": ", ".join(str(x) for x in pattern.get("evidence_types", [])),
                "sample_size": sample_size,
            }
        )

    # Keep the service robust if a caller supplies qualified signals without
    # a separate pattern object. The signal text is already evidence-backed.
    if not observations:
        for signal in signals[:8]:
            sample_size = int(signal.get("sample_size", 0))
            if sample_size < minimum:
                continue
            observations.append(
                {
                    "title": str(signal.get("label", "Observed signal")),
                    "description": str(signal.get("description", "")),
                    "evidence_source": "observed_signal",
                    "sample_size": sample_size,
                }
            )

    convergence = cross_lens_analysis.get("convergence", []) if cross_lens_analysis else []
    divergence = cross_lens_analysis.get("divergence", []) if cross_lens_analysis else []
    if convergence:
        observations.append(
            {
                "title": "Observed convergence",
                "description": convergence[0].get("description", "Qualifying cohorts show a shared observed pattern."),
                "evidence_source": "cross_lens_convergence",
                "sample_size": min(
                    int(convergence[0].get("sample_size_a", 0)),
                    int(convergence[0].get("sample_size_b", 0)),
                ),
            }
        )
    if divergence:
        observations.append(
            {
                "title": "Observed divergence",
                "description": divergence[0].get("description", "Qualifying cohorts show an observed difference."),
                "evidence_source": "cross_lens_divergence",
                "sample_size": min(
                    int(divergence[0].get("sample_size_a", 0)),
                    int(divergence[0].get("sample_size_b", 0)),
                ),
            }
        )

    temporal_data = temporal or {}
    temporal_changes = temporal_data.get("changes", [])
    if temporal_changes:
        changed = [change for change in temporal_changes if change.get("stance_changed") or change.get("theme_changed")]
        if changed:
            change = changed[-1]
            observations.append(
                {
                    "title": "Observed temporal change",
                    "description": (
                        "A qualifying time-window comparison recorded a change in "
                        f"{'leading stance' if change.get('stance_changed') else ''}"
                        f"{' and ' if change.get('stance_changed') and change.get('theme_changed') else ''}"
                        f"{'leading theme' if change.get('theme_changed') else ''}."
                    ),
                    "evidence_source": "temporal_change",
                    "sample_size": min(int(change.get("sample_size_from", 0)), int(change.get("sample_size_to", 0))),
                }
            )

    observations = [item for item in observations if item["sample_size"] >= minimum][:10]
    status = "available" if has_evidence and observations else "insufficient_sample"

    considerations = [
        {"title": title, "description": guidance},
        {
            "title": "Evidence boundary",
            "description": "The framing does not add evidence or change the underlying measurements, samples, periods, or cohort definitions.",
        },
    ]
    if not observations:
        summary = f"Decision intelligence is withheld until at least {minimum} analyzed comments qualify for semantic evidence."
    else:
        summary = f"{len(observations)} evidence-backed observation(s) are available under the {normalized.replace('_', ' ')} decision lens."

    return {
        "intent": normalized,
        "status": status,
        "summary": summary,
        "observations": observations,
        "considerations": considerations,
        "evidence_invariant": True,
        "guardrail": "Decision framing changes relevance and next-step context; it does not establish causation, prediction, or population-wide conclusions.",
        "limitations": [
            "Observed platform discussion may not be representative of the wider population.",
            "Decision framing is not professional, legal, clinical, financial, or policy advice.",
            "Individual participant identities are not exposed.",
        ],
    }
