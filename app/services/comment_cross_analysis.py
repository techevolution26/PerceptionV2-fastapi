"""Privacy-safe professional and geographic semantic cross-analysis."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from app.models.models import CommentIntelligence, User
from app.services.professional_taxonomy import ROLE_MAP

CROSS_ANALYSIS_MINIMUM = 5


def _distribution(values: Iterable[str | None]) -> list[dict]:
    counts = Counter(value for value in values if value)
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        {"label": label, "comments": count, "share": round(count / total, 3)}
        for label, count in counts.most_common()
    ]


def _themes(rows: Iterable[CommentIntelligence]) -> list[dict]:
    counts: Counter[str] = Counter()
    for row in rows:
        for theme in row.themes or []:
            label = str(theme).strip()
            if label:
                counts[label] += 1
    total = sum(counts.values())
    if total == 0:
        return []
    return [
        {"theme": label, "comments": count, "share": round(count / total, 3)}
        for label, count in counts.most_common(5)
    ]


def _segment(rows: list[CommentIntelligence], *, key: str, label: str) -> dict:
    quality = [r.quality_score for r in rows if r.quality_score is not None]
    return {
        key: label,
        "sample_size": len(rows),
        "sentiment_distribution": _distribution(r.sentiment for r in rows),
        "stance_distribution": _distribution(r.stance for r in rows),
        "top_themes": _themes(rows),
        "question_count": sum(1 for r in rows if r.is_question),
        "quality_score": round(sum(quality) / len(quality), 3) if quality else None,
    }


def aggregate_professional_geographic_semantics(
    rows: list[tuple[CommentIntelligence, User]],
    *,
    minimum: int = CROSS_ANALYSIS_MINIMUM,
) -> dict:
    """Aggregate analyzed comments by professional and geographic cohorts.

    A comment belongs to its author's primary professional role, country and
    country-region. Each reported cohort must independently meet the minimum
    comment sample. No participant identity is returned.
    """
    if len(rows) < minimum:
        return {
            "cross_analysis_status": "insufficient_sample",
            "cross_analysis_note": (
                f"Professional and geographic semantic comparison is withheld "
                f"until at least {minimum} analyzed comments are available."
            ),
            "cross_analysis_sample_minimum": minimum,
            "cross_analysis_comment_count": len(rows),
            "professional_semantic_segments": [],
            "geographic_semantic_segments": [],
            "professional_geographic_segments": [],
        }

    professional: defaultdict[str, list[CommentIntelligence]] = defaultdict(list)
    geographic: defaultdict[str, list[CommentIntelligence]] = defaultdict(list)
    cross: defaultdict[tuple[str, str], list[CommentIntelligence]] = defaultdict(list)

    for intelligence, user in rows:
        role = user.primary_professional_role
        if not role and user.profession:
            role = user.profession.strip()
        country = (user.country_code or "UNKNOWN").upper()
        region = (user.region or "UNKNOWN").strip()
        geo = f"{country} · {region}" if region != "UNKNOWN" else country

        if role:
            professional[str(role)].append(intelligence)
            cross[(str(role), geo)].append(intelligence)
        geographic[geo].append(intelligence)

    professional_segments = []
    for role, segment_rows in professional.items():
        if len(segment_rows) >= minimum:
            item = _segment(segment_rows, key="role_code", label=role)
            item["role_label"] = ROLE_MAP.get(role, {}).get("label", role)
            professional_segments.append(item)

    geographic_segments = []
    for geo, segment_rows in geographic.items():
        if len(segment_rows) >= minimum:
            geographic_segments.append(
                _segment(segment_rows, key="geography", label=geo)
            )

    cross_segments = []
    for (role, geo), segment_rows in cross.items():
        if len(segment_rows) >= minimum:
            item = _segment(segment_rows, key="role_code", label=role)
            item["role_label"] = ROLE_MAP.get(role, {}).get("label", role)
            item["geography"] = geo
            cross_segments.append(item)

    professional_segments.sort(key=lambda item: item["sample_size"], reverse=True)
    geographic_segments.sort(key=lambda item: item["sample_size"], reverse=True)
    cross_segments.sort(key=lambda item: item["sample_size"], reverse=True)

    return {
        "cross_analysis_status": "available" if (professional_segments or geographic_segments) else "insufficient_segments",
        "cross_analysis_note": (
            "Semantic signals are compared only across cohorts that meet the minimum sample. "
            "Professional cohorts use primary professional identity; geography uses country and region."
        ),
        "cross_analysis_sample_minimum": minimum,
        "cross_analysis_comment_count": len(rows),
        "professional_semantic_segments": professional_segments[:10],
        "geographic_semantic_segments": geographic_segments[:10],
        "professional_geographic_segments": cross_segments[:15],
    }
