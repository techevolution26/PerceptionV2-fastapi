"""Deterministic longitudinal intelligence across one user's authored Perceptions.

This layer summarizes stored comment-semantic evidence over the user's authored
Perceptions and Topics. It does not infer traits, causality, or future outcomes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.models.models import CommentIntelligence, Perception, Topic

PROFILE_INTELLIGENCE_SCHEMA_VERSION = "1.0"
PROFILE_SAMPLE_MINIMUM = 5
PROFILE_BUCKET_DAYS = 30
PROFILE_WINDOW_DAYS = 180


def _distribution(values: list[str | None]) -> list[dict[str, Any]]:
    counts = Counter(v for v in values if v)
    total = sum(counts.values())
    if not total:
        return []
    return [
        {"label": label, "comments": count, "share": round(count / total, 3)}
        for label, count in counts.most_common()
    ]


def _themes(rows: list[CommentIntelligence], limit: int = 10) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        for theme in row.themes or []:
            label = str(theme).strip()
            if label:
                counts[label] += 1
    total = sum(counts.values())
    return [
        {"theme": theme, "comments": count, "share": round(count / total, 3)}
        for theme, count in counts.most_common(limit)
    ] if total else []


def _quality(rows: list[CommentIntelligence]) -> float | None:
    values = [r.quality_score for r in rows if r.quality_score is not None]
    return round(sum(values) / len(values), 3) if values else None


def build_profile_intelligence(
    *,
    perceptions: list[Perception],
    semantic_rows: list[tuple[CommentIntelligence, int, int | None, str | None, datetime]],
    period_start: datetime,
    period_end: datetime,
    minimum: int = PROFILE_SAMPLE_MINIMUM,
) -> dict[str, Any]:
    """Build portfolio/topic/temporal intelligence from stored evidence.

    semantic_rows are (comment intelligence, perception_id, topic_name, created_at).
    Only analyzed rows supplied by the route are eligible evidence.
    """
    rows = semantic_rows
    by_perception: dict[int, list[CommentIntelligence]] = defaultdict(list)
    by_topic: dict[tuple[int | None, str], list[CommentIntelligence]] = defaultdict(list)
    theme_topics: dict[str, set[str]] = defaultdict(set)
    theme_comments: Counter[str] = Counter()

    for intelligence, perception_id, topic_id, topic_name, _created_at in rows:
        by_perception[perception_id].append(intelligence)
        key = (topic_id, topic_name or "Uncategorized")
        by_topic[key].append(intelligence)
        for theme in intelligence.themes or []:
            label = str(theme).strip()
            if label:
                theme_topics[label].add(topic_name or "Uncategorized")
                theme_comments[label] += 1

    perception_topic = {p.id: (p.topic_id, p.topic.name if p.topic else "Uncategorized") for p in perceptions}
    qualifying_perceptions = sum(len(by_perception.get(p.id, [])) >= minimum for p in perceptions)

    topic_perception_counts: Counter[str] = Counter()
    for p in perceptions:
        topic_perception_counts[p.topic.name if p.topic else "Uncategorized"] += 1

    topic_sections: list[dict[str, Any]] = []
    for (topic_id, topic_name), topic_rows in sorted(by_topic.items(), key=lambda item: len(item[1]), reverse=True):
        if len(topic_rows) < minimum:
            continue
        topic_sections.append({
            "topic_id": topic_id,
            "topic_name": topic_name,
            "perception_count": topic_perception_counts.get(topic_name, 0),
            "sample_size": len(topic_rows),
            "sentiment_distribution": _distribution([r.sentiment for r in topic_rows]),
            "stance_distribution": _distribution([r.stance for r in topic_rows]),
            "top_themes": _themes(topic_rows, 5),
            "question_count": sum(bool(r.is_question) for r in topic_rows),
            "quality_score": _quality(topic_rows),
        })

    recurring_themes = [
        {
            "theme": theme,
            "comment_count": theme_comments[theme],
            "topic_count": len(topic_set),
            "topics": sorted(topic_set)[:10],
        }
        for theme, topic_set in sorted(
            theme_topics.items(), key=lambda item: (len(item[1]), theme_comments[item[0]]), reverse=True
        )
        if len(topic_set) >= 2 and theme_comments[theme] >= minimum
    ][:10]

    buckets: list[dict[str, Any]] = []
    bucket_end = period_end
    while bucket_end > period_start:
        bucket_start = max(period_start, bucket_end - timedelta(days=PROFILE_BUCKET_DAYS))
        bucket_rows = [
            intelligence
            for intelligence, _pid, _topic_id, _topic, created_at in rows
            if bucket_start <= created_at < bucket_end
        ]
        sample = len(bucket_rows)
        if sample >= minimum:
            themes = _themes(bucket_rows, 5)
            buckets.append({
                "period_start": bucket_start,
                "period_end": bucket_end,
                "sample_size": sample,
                "status": "available",
                "sentiment_distribution": _distribution([r.sentiment for r in bucket_rows]),
                "stance_distribution": _distribution([r.stance for r in bucket_rows]),
                "top_themes": themes,
                "question_count": sum(bool(r.is_question) for r in bucket_rows),
                "quality_score": _quality(bucket_rows),
            })
        bucket_end = bucket_start

    buckets.reverse()
    patterns: list[dict[str, Any]] = []
    if recurring_themes:
        first = recurring_themes[0]
        patterns.append({
            "label": "Recurring theme across Topics",
            "description": f"The theme '{first['theme']}' appears in responses across {first['topic_count']} Topics.",
            "sample_size": first["comment_count"],
            "limitations": ["Theme recurrence is observational and does not establish why the theme recurs."],
        })
    if len(topic_sections) >= 2:
        patterns.append({
            "label": "Multiple qualifying Topics",
            "description": f"{len(topic_sections)} Topics have at least {minimum} analyzed comments in the selected period.",
            "sample_size": sum(item["sample_size"] for item in topic_sections),
            "limitations": ["Topic-level samples are not necessarily population-representative."],
        })
    if len(buckets) >= 2:
        first_stance = next((x["label"] for x in buckets[0]["stance_distribution"]), None)
        last_stance = next((x["label"] for x in buckets[-1]["stance_distribution"]), None)
        if first_stance and last_stance and first_stance != last_stance:
            patterns.append({
                "label": "Longitudinal stance change",
                "description": "The leading observed stance differs between qualifying time windows.",
                "sample_size": min(buckets[0]["sample_size"], buckets[-1]["sample_size"]),
                "limitations": ["A change in observed stance does not establish causation or a durable change in audience attitude."],
            })

    return {
        "schema_version": PROFILE_INTELLIGENCE_SCHEMA_VERSION,
        "period_days": (period_end - period_start).days,
        "sample_minimum": minimum,
        "perception_count": len(perceptions),
        "topic_count": len({perception_topic[p.id][0] for p in perceptions if perception_topic[p.id][0] is not None}),
        "analyzed_comment_count": len(rows),
        "qualifying_perception_count": qualifying_perceptions,
        "topics": topic_sections,
        "recurring_themes": recurring_themes,
        "temporal": {
            "bucket_days": PROFILE_BUCKET_DAYS,
            "qualifying_bucket_count": len(buckets),
            "buckets": buckets,
            "status": "available" if buckets else "insufficient_sample",
            "note": f"Only time windows with at least {minimum} analyzed comments are shown.",
        },
        "patterns": patterns,
        "limitations": [
            "Profile intelligence summarizes the user's authored Perceptions and their analyzed responses.",
            "Topic and professional identity are separate dimensions; no authority over a Topic is inferred from professional identity.",
            "Platform observations are not automatically population-representative.",
            "Observational patterns do not establish causation or prediction.",
            "Individual participant identities are not exposed.",
        ],
    }
