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
        {"label": label, "count": count, "share": round(count / total, 3)}
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
    return {
        "schema_version": INTELLIGENCE_SCHEMA_VERSION,
        "topic": {"id": topic_id, "name": topic_name},
        "perception_id": perception_id,
        "period_days": period_days,
        "semantic": semantic,
        "cross_lens": cross,
    }
