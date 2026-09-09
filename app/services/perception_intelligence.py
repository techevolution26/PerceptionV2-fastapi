"""Deterministic orchestration for Perception Intelligence.

This layer does not call an AI provider. It composes platform measurements,
stored comment-semantic evidence, and qualifying contextual lenses into a
stable, evidence-scoped intelligence envelope.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Iterable

from app.models.models import CommentIntelligence, User

INTELLIGENCE_SCHEMA_VERSION = "1.0"
MINIMUM_SAMPLE = 5


def _distribution(values: Iterable[str | None]) -> list[dict[str, Any]]:
    counts = Counter(value for value in values if value)
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        {"label": label, "comments": count, "share": round(count / total, 3)}
        for label, count in counts.most_common()
    ]


def _evidence_status(sample_size: int, minimum: int = MINIMUM_SAMPLE) -> str:
    return "available" if sample_size >= minimum else "insufficient_sample"


def build_evidence_envelope(
    *,
    topic_id: int | None,
    topic_name: str | None,
    perception_id: int,
    period_start: datetime,
    period_end: datetime,
    sample_size: int,
    scope: str,
    evidence: list[dict[str, Any]],
    lens: dict[str, Any] | None = None,
    quality_score: float | None = None,
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Build a stable envelope around an observed analytical result."""
    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "topic": {"id": topic_id, "name": topic_name},
        "perception_id": perception_id,
        "scope": scope,
        "period": {"start": period_start, "end": period_end},
        "lens": lens,
        "sample_size": sample_size,
        "sample_minimum": minimum,
        "evidence_status": _evidence_status(sample_size, minimum),
        "evidence": evidence,
        "quality_score": quality_score,
        "limitations": [
            "Platform observations are not automatically population-representative.",
            "Observational patterns do not establish causation.",
        ],
    }


def build_semantic_evidence(
    rows: list[CommentIntelligence],
    *,
    topic_id: int | None,
    topic_name: str | None,
    perception_id: int,
    period_start: datetime,
    period_end: datetime,
    period_days: int,
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Compose stored semantic results into evidence without generating claims."""
    sample_size = len(rows)
    quality_values = [r.quality_score for r in rows if r.quality_score is not None]
    quality = round(sum(quality_values) / len(quality_values), 3) if quality_values else None

    themes = Counter(
        str(theme).strip()
        for row in rows
        for theme in (row.themes or [])
        if str(theme).strip()
    )
    theme_total = sum(themes.values())
    top_themes = [
        {"theme": theme, "comments": count, "share": round(count / theme_total, 3)}
        for theme, count in themes.most_common(10)
    ] if theme_total else []

    def flagged_themes(flag: str) -> list[dict]:
        counts: Counter[str] = Counter()
        for row in rows:
            if not getattr(row, flag):
                continue
            for theme in row.themes or []:
                label = str(theme).strip()
                if label:
                    counts[label] += 1
        total = sum(counts.values())
        return [
            {"theme": theme, "comments": count, "share": round(count / total, 3)}
            for theme, count in counts.most_common(10)
        ] if total else []

    evidence = [
        {
            "type": "sentiment_distribution",
            "observed": _distribution(row.sentiment for row in rows),
        },
        {
            "type": "stance_distribution",
            "observed": _distribution(row.stance for row in rows),
        },
        {"type": "top_themes", "observed": top_themes},
        {"type": "question_count", "observed": sum(1 for row in rows if row.is_question)},
        {"type": "concern_themes", "observed": flagged_themes("has_concern")},
        {"type": "agreement_themes", "observed": flagged_themes("agreement_signal")},
        {"type": "disagreement_themes", "observed": flagged_themes("disagreement_signal")},
    ]

    envelope = build_evidence_envelope(
        topic_id=topic_id,
        topic_name=topic_name,
        perception_id=perception_id,
        period_start=period_start,
        period_end=period_end,
        sample_size=sample_size,
        scope="perception_semantic_response_population",
        evidence=evidence if sample_size >= minimum else [],
        quality_score=quality if sample_size >= minimum else None,
        minimum=minimum,
    )
    return {
        "semantic_evidence": envelope,
        "period_days": period_days,
        "analyzed_comment_count": sample_size,
    }


def build_cross_lens_evidence(
    *,
    topic_id: int | None,
    topic_name: str | None,
    perception_id: int,
    period_start: datetime,
    period_end: datetime,
    total_analyzed_comments: int,
    professional_segments: list[dict],
    geographic_segments: list[dict],
    professional_geographic_segments: list[dict],
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Wrap deterministic cohort outputs in the common evidence contract."""
    available = total_analyzed_comments >= minimum
    evidence = [
        {"type": "professional_perspectives", "observed": professional_segments},
        {"type": "geographic_perspectives", "observed": geographic_segments},
        {"type": "professional_geographic_perspectives", "observed": professional_geographic_segments},
    ]
    return build_evidence_envelope(
        topic_id=topic_id,
        topic_name=topic_name,
        perception_id=perception_id,
        period_start=period_start,
        period_end=period_end,
        sample_size=total_analyzed_comments,
        scope="perception_cross_lens_response_population",
        evidence=evidence if available else [],
        minimum=minimum,
    )


def qualify_signal(
    *,
    label: str,
    description: str,
    evidence: dict[str, Any],
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any] | None:
    """Create a signal wrapper only when the supporting sample qualifies.

    This function deliberately accepts a caller-supplied description rather
    than asking an LLM to invent one. The description must therefore remain an
    evidence-backed, scoped statement supplied by deterministic application
    logic.
    """
    sample_size = int(evidence.get("sample_size", 0))
    if sample_size < minimum:
        return None
    return {
        "label": label,
        "description": description,
        "evidence": evidence,
        "status": "observed_signal",
        "limitations": evidence.get("limitations", []),
    }


def decision_context(
    *,
    intent: str,
    signals: list[dict[str, Any]],
) -> dict[str, Any]:
    """Frame existing signals for a decision intent without changing evidence."""
    allowed = {
        "research",
        "business",
        "policy",
        "journalism",
        "education",
        "product",
        "professional",
        "general_exploration",
    }
    normalized = intent.lower().strip()
    if normalized not in allowed:
        raise ValueError(f"Unsupported decision intent: {intent}")
    return {
        "intent": normalized,
        "signals": signals,
        "evidence_invariant": True,
        "guardrail": "Decision context reframes observed evidence; it does not establish causation or prediction.",
    }




def _dominant_label(segment: dict[str, Any], field: str) -> str | None:
    values = segment.get(field) or []
    if not values:
        return None
    value = values[0]
    return str(value.get("label")) if isinstance(value, dict) and value.get("label") else None


def _theme_labels(segment: dict[str, Any], limit: int = 3) -> set[str]:
    return {
        str(item.get("theme")).strip()
        for item in (segment.get("top_themes") or [])[:limit]
        if isinstance(item, dict) and str(item.get("theme", "")).strip()
    }


def analyze_cross_lens_divergence(
    *,
    professional_segments: list[dict[str, Any]],
    geographic_segments: list[dict[str, Any]],
    cross_lens_segments: list[dict[str, Any]],
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Compare qualifying cohorts without identifying or ranking individuals.

    Convergence requires the same leading stance and at least one shared theme.
    Divergence is reported when leading stances differ, or when stances match
    but the leading themes do not overlap. These are descriptive comparisons,
    not explanations of why cohorts differ.
    """
    groups = {
        "professional": professional_segments,
        "geographic": geographic_segments,
        "professional_geographic": cross_lens_segments,
    }
    convergence: list[dict[str, Any]] = []
    divergence: list[dict[str, Any]] = []

    for dimension, segments in groups.items():
        qualifying = [s for s in segments if int(s.get("sample_size", 0)) >= minimum]
        for index, left in enumerate(qualifying):
            for right in qualifying[index + 1:]:
                left_stance = _dominant_label(left, "stance_distribution")
                right_stance = _dominant_label(right, "stance_distribution")
                shared_themes = sorted(_theme_labels(left) & _theme_labels(right))
                left_label = (
                    f"{left.get('role_label', left.get('role_code'))} · {left.get('geography')}"
                    if dimension == "professional_geographic"
                    else left.get("role_label", left.get("geography", left.get("role_code")))
                )
                right_label = (
                    f"{right.get('role_label', right.get('role_code'))} · {right.get('geography')}"
                    if dimension == "professional_geographic"
                    else right.get("role_label", right.get("geography", right.get("role_code")))
                )
                base = {
                    "dimension": dimension,
                    "cohort_a": str(left_label),
                    "cohort_b": str(right_label),
                    "sample_size_a": int(left.get("sample_size", 0)),
                    "sample_size_b": int(right.get("sample_size", 0)),
                    "leading_stance_a": left_stance,
                    "leading_stance_b": right_stance,
                    "shared_themes": shared_themes,
                }
                if left_stance and left_stance == right_stance and shared_themes:
                    convergence.append({
                        **base,
                        "type": "stance_and_theme_convergence",
                        "description": (
                            f"{left_label} and {right_label} share the same leading stance "
                            f"and at least one of their leading themes."
                        ),
                    })
                elif left_stance and right_stance and left_stance != right_stance:
                    divergence.append({
                        **base,
                        "type": "stance_divergence",
                        "description": (
                            f"{left_label} and {right_label} have different leading stances "
                            f"within the observed response sample."
                        ),
                    })
                elif left_stance and left_stance == right_stance and not shared_themes:
                    divergence.append({
                        **base,
                        "type": "thematic_divergence",
                        "description": (
                            f"{left_label} and {right_label} share the same leading stance "
                            f"but have no overlapping themes among their leading recorded themes."
                        ),
                    })

    convergence.sort(key=lambda item: (item["dimension"], -min(item["sample_size_a"], item["sample_size_b"])))
    divergence.sort(key=lambda item: (item["dimension"], -min(item["sample_size_a"], item["sample_size_b"])))
    return {
        "status": "available" if (convergence or divergence) else "insufficient_comparison",
        "sample_minimum": minimum,
        "convergence": convergence[:20],
        "divergence": divergence[:20],
        "note": (
            "Comparisons are descriptive and limited to qualifying cohorts. "
            "They show where observed leading stances or themes align or differ; "
            "they do not explain causes or represent population-wide opinion."
        ),
    }

def derive_patterns_and_signals(
    *,
    semantic_evidence: dict[str, Any],
    cross_lens_evidence: dict[str, Any],
    cross_lens_comparison: dict[str, Any] | None = None,
    minimum: int = MINIMUM_SAMPLE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive only deterministic, descriptive patterns from qualified evidence.

    This layer intentionally avoids causal, predictive, or motivational claims.
    A pattern is emitted only when the underlying evidence envelope is qualified.
    A signal is a compact observed statement backed by that same evidence.
    """
    if semantic_evidence.get("sample_size", 0) < minimum:
        return [], []

    evidence_items = {
        item["type"]: item["observed"]
        for item in semantic_evidence.get("evidence", [])
        if isinstance(item, dict) and "type" in item
    }
    patterns: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []

    def add(label: str, description: str, evidence_types: list[str]) -> None:
        patterns.append({
            "label": label,
            "description": description,
            "evidence_types": evidence_types,
        })

    sentiment = evidence_items.get("sentiment_distribution", [])
    if sentiment:
        dominant = sentiment[0]
        add(
            "Dominant sentiment",
            f"{dominant['label'].replace('_', ' ').capitalize()} is the most common sentiment in the analyzed comments ({dominant['comments']} of {semantic_evidence['sample_size']}).",
            ["sentiment_distribution"],
        )

    stance = evidence_items.get("stance_distribution", [])
    if stance:
        dominant = stance[0]
        add(
            "Dominant stance",
            f"{dominant['label'].replace('_', ' ').capitalize()} is the most common stance in the analyzed comments ({dominant['comments']} of {semantic_evidence['sample_size']}).",
            ["stance_distribution"],
        )

    themes = evidence_items.get("top_themes", [])
    if themes:
        top = themes[0]
        add(
            "Recurring theme",
            f"The theme '{top['theme']}' occurs in {top['comments']} analyzed comments and is the most frequent recorded theme.",
            ["top_themes"],
        )

    question_count = int(evidence_items.get("question_count", 0) or 0)
    if question_count:
        add(
            "Question activity",
            f"{question_count} analyzed comments contain a question signal.",
            ["question_count"],
        )

    concern_themes = evidence_items.get("concern_themes", [])
    if concern_themes:
        top = concern_themes[0]
        add(
            "Concern theme",
            f"'{top['theme']}' is the most frequent theme among comments carrying a concern signal ({top['comments']} comments).",
            ["concern_themes"],
        )

    agreement = evidence_items.get("agreement_themes", [])
    disagreement = evidence_items.get("disagreement_themes", [])
    if agreement and disagreement:
        add(
            "Mixed response signals",
            "The analyzed comments contain both agreement and disagreement signals, indicating a mixed response pattern within the observed discussion.",
            ["agreement_themes", "disagreement_themes"],
        )

    cross_sample = cross_lens_evidence.get("sample_size", 0)
    if cross_sample >= minimum:
        professional = [
            item for item in cross_lens_evidence.get("evidence", [])[0].get("observed", [])
            if isinstance(item, dict)
        ] if cross_lens_evidence.get("evidence") else []
        geographic = [
            item for item in cross_lens_evidence.get("evidence", [])[1].get("observed", [])
            if isinstance(item, dict)
        ] if len(cross_lens_evidence.get("evidence", [])) > 1 else []
        if len(professional) >= 2 or len(geographic) >= 2:
            add(
                "Multiple qualifying perspectives",
                "The discussion contains multiple professional or geographic cohorts that independently meet the minimum analytical sample.",
                ["professional_perspectives", "geographic_perspectives"],
            )

    comparison = cross_lens_comparison or {}
    convergence = comparison.get("convergence", [])
    divergence = comparison.get("divergence", [])
    if convergence:
        first = convergence[0]
        add(
            "Cross-lens convergence",
            first["description"],
            ["cross_lens_convergence"],
        )
    if divergence:
        first = divergence[0]
        add(
            "Cross-lens divergence",
            first["description"],
            ["cross_lens_divergence"],
        )

    # Signals deliberately reuse pattern descriptions and carry the exact
    # evidence sample/limitations instead of introducing stronger claims.
    for pattern in patterns:
        evidence = semantic_evidence
        if any(kind in pattern["evidence_types"] for kind in (
            "professional_perspectives", "geographic_perspectives",
            "cross_lens_convergence", "cross_lens_divergence",
        )):
            evidence = cross_lens_evidence
        signals.append({
            "label": pattern["label"],
            "description": pattern["description"],
            "status": "observed_signal",
            "sample_size": int(evidence.get("sample_size", 0)),
            "limitations": evidence.get("limitations", []),
        })

    return patterns, signals

def orchestrate_perception_intelligence(
    *,
    topic_id: int | None,
    topic_name: str | None,
    perception_id: int,
    period_start: datetime,
    period_end: datetime,
    period_days: int,
    semantic_rows: list[CommentIntelligence],
    participant_rows: list[tuple[CommentIntelligence, User]],
    cross_lens: dict[str, Any],
    scope: str = "conversation_intelligence",
    viewer_lens: str = "observer",
    minimum: int = MINIMUM_SAMPLE,
) -> dict[str, Any]:
    """Compose the deterministic v1 intelligence layers for one Perception.

    ``cross_lens`` is deliberately supplied by the existing cohort service so
    this orchestrator owns composition, not cohort-specific business rules.
    """
    semantic = build_semantic_evidence(
        semantic_rows,
        topic_id=topic_id,
        topic_name=topic_name,
        perception_id=perception_id,
        period_start=period_start,
        period_end=period_end,
        period_days=period_days,
        minimum=minimum,
    )
    cross = build_cross_lens_evidence(
        topic_id=topic_id,
        topic_name=topic_name,
        perception_id=perception_id,
        period_start=period_start,
        period_end=period_end,
        total_analyzed_comments=len(participant_rows),
        professional_segments=cross_lens.get("professional_semantic_segments", []),
        geographic_segments=cross_lens.get("geographic_semantic_segments", []),
        professional_geographic_segments=cross_lens.get("professional_geographic_segments", []),
        minimum=minimum,
    )
    cross_lens_comparison = analyze_cross_lens_divergence(
        professional_segments=cross_lens.get("professional_semantic_segments", []),
        geographic_segments=cross_lens.get("geographic_semantic_segments", []),
        cross_lens_segments=cross_lens.get("professional_geographic_segments", []),
        minimum=minimum,
    )
    patterns, signals = derive_patterns_and_signals(
        semantic_evidence=semantic["semantic_evidence"],
        cross_lens_evidence=cross,
        cross_lens_comparison=cross_lens_comparison,
        minimum=minimum,
    )

    semantic_evidence = semantic["semantic_evidence"]
    semantic_quality = semantic_evidence.get("quality_score")
    common_limitations = semantic_evidence.get("limitations", [])

    def provenance_for(evidence_types: list[str], source: str, sample_size: int, quality_score: float | None) -> dict[str, Any]:
        qualified = sample_size >= minimum
        return {
            "source": source,
            "evidence_types": evidence_types,
            "sample_size": sample_size,
            "period_start": period_start,
            "period_end": period_end,
            "scope": scope,
            "viewer_lens": viewer_lens,
            "quality_score": quality_score,
            "qualification": (
                f"Qualified because the evidence sample meets the minimum of {minimum} observations."
                if qualified
                else f"Not qualified because the evidence sample is below the minimum of {minimum} observations."
            ),
            "limitations": common_limitations,
        }

    semantic_provenance = provenance_for(
        ["comment_semantics"],
        "comment_intelligence",
        int(semantic_evidence.get("sample_size", 0)),
        semantic_quality,
    )
    cross_provenance = provenance_for(
        ["professional_perspectives", "geographic_perspectives", "cross_lens_comparison"],
        "cross_lens_analysis",
        int(cross.get("sample_size", 0)),
        None,
    )

    for pattern in patterns:
        pattern["provenance"] = (
            cross_provenance if any(kind in pattern.get("evidence_types", []) for kind in (
                "professional_perspectives", "geographic_perspectives",
                "cross_lens_convergence", "cross_lens_divergence",
            )) else semantic_provenance
        )
    for signal in signals:
        signal["provenance"] = (
            cross_provenance if signal.get("label") in {
                "Multiple qualifying perspectives", "Cross-lens convergence", "Cross-lens divergence"
            } else semantic_provenance
        )

    root_provenance = provenance_for(
        ["comment_semantics", "comment_participants", "cross_lens_analysis", "temporal_intelligence"],
        "comment_intelligence",
        len(semantic_rows),
        semantic_quality,
    )

    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "topic": {"id": topic_id, "name": topic_name},
        "perception_id": perception_id,
        "period_days": period_days,
        "semantic": semantic,
        "cross_lens": cross,
        "cross_lens_comparison": cross_lens_comparison,
        "patterns": patterns,
        "signals": signals,
        "provenance": root_provenance,
    }
