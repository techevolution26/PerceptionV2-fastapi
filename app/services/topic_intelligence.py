"""Deterministic intelligence aggregated across public Perceptions under one Topic.

This layer consumes stored comment-semantic evidence. It never calls an AI
provider, never exposes participant identities, and never treats a single
Perception as equivalent to a Topic-wide finding.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from app.models.models import CommentIntelligence, User
from app.services.comment_intelligence import aggregate_comment_intelligence
from app.services.comment_cross_analysis import (
    aggregate_professional_geographic_semantics,
)
from app.services.perception_intelligence import analyze_cross_lens_divergence
from app.services.intelligence_freshness import _aware

TOPIC_INTELLIGENCE_SCHEMA_VERSION = "1.0"
TOPIC_SAMPLE_MINIMUM = 5
TOPIC_PERCEPTION_MINIMUM = 2
TOPIC_PARTICIPANT_MINIMUM = 5
TOPIC_BUCKET_DAYS = 30


def _dist(values: list[str | None]) -> list[dict[str, Any]]:
    counts = Counter(value for value in values if value)
    total = sum(counts.values())
    return (
        [
            {"label": label, "comments": count, "share": round(count / total, 3)}
            for label, count in counts.most_common()
        ]
        if total
        else []
    )


def _themes(rows: list[CommentIntelligence], limit: int = 5) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        for theme in row.themes or []:
            label = str(theme).strip()
            if label:
                counts[label] += 1
    total = sum(counts.values())
    return (
        [
            {"theme": label, "comments": count, "share": round(count / total, 3)}
            for label, count in counts.most_common(limit)
        ]
        if total
        else []
    )


def _quality(rows: list[CommentIntelligence]) -> float | None:
    values = [r.quality_score for r in rows if r.quality_score is not None]
    return round(sum(values) / len(values), 3) if values else None


def _trace_id(topic_id: int, period_start: datetime, period_end: datetime) -> str:
    return f"topic:{topic_id}:{period_start.isoformat()}:{period_end.isoformat()}"


def build_topic_intelligence(
    *,
    topic_id: int,
    topic_name: str,
    semantic_rows: list[tuple[CommentIntelligence, int, datetime]],
    participant_rows: list[tuple[CommentIntelligence, User]],
    period_start: datetime,
    period_end: datetime,
    access_tier: str,
    upgrade_available: bool,
    upgrade_message: str | None,
    decision_intent: str = "general_exploration",
    minimum: int = TOPIC_SAMPLE_MINIMUM,
    perception_minimum: int = TOPIC_PERCEPTION_MINIMUM,
    participant_minimum: int = TOPIC_PARTICIPANT_MINIMUM,
    quality_report: dict[str, Any] | None = None,
    freshness: dict[str, Any] | None = None,
    evidence_governance: dict[str, Any] | None = None,
    semantic_model_governance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_report = quality_report or {
        "status": "not_ready",
        "analyzed_comment_count": 0,
        "quality_score": None,
        "low_quality_comment_count": 0,
        "low_quality_share": None,
        "failed_comment_count": 0,
        "pending_comment_count": 0,
        "model_versions": [],
        "note": "Quality metrics were not computed for this request.",
        "limitations": [],
    }
    freshness = freshness or {
        "status": "current",
        "recalculation_required": False,
        "source_comment_count": 0,
        "analyzed_comment_count": 0,
        "pending_comment_count": 0,
        "failed_comment_count": 0,
        "latest_source_at": None,
        "latest_analysis_at": None,
        "note": "Freshness was not computed for this request.",
    }
    evidence_governance = evidence_governance or {
        "status": "restricted",
        "minimum_sample": minimum,
        "analyzed_comment_count": 0,
        "pending_comment_count": 0,
        "failed_comment_count": 0,
        "quality_threshold": 0.60,
        "quality_score": None,
        "freshness_status": freshness["status"],
        "patterns_eligible": False,
        "signals_eligible": False,
        "reasons": ["Evidence governance was not computed for this request."],
        "rules": [],
    }
    semantic_model_governance = semantic_model_governance or {
        "status": "insufficient_sample",
        "active_model_versions": [],
        "baseline_model_version": None,
        "latest_model_version": None,
        "compared_sample_size": 0,
        "distribution_shifts": [],
        "note": "Model governance was not computed for this request.",
        "limitations": [],
    }

    # Postgres returns timezone-aware datetimes for DateTime(timezone=True)
    # columns; SQLite (used in the fast local test suite) does not. Normalize
    # once at the entry point so every downstream comparison against
    # period_start/period_end (always aware) is safe on both backends.
    rows = [(row, pid, _aware(created_at)) for row, pid, created_at in semantic_rows]
    by_perception: dict[int, list[CommentIntelligence]] = defaultdict(list)
    for intelligence, perception_id, _created_at in rows:
        by_perception[perception_id].append(intelligence)

    qualifying = {
        perception_id: values
        for perception_id, values in by_perception.items()
        if len(values) >= minimum
    }
    analyzed_count = len(rows)
    qualifying_count = len(qualifying)
    unique_participants = len({user.id for _intelligence, user in participant_rows})

    semantic_status = "available"
    if analyzed_count < minimum:
        semantic_status = "insufficient_sample"
    elif qualifying_count < perception_minimum:
        semantic_status = "insufficient_breadth"
    elif unique_participants < participant_minimum:
        semantic_status = "insufficient_participants"

    semantic = aggregate_comment_intelligence(
        [row for row, _pid, _created_at in rows],
        period_days=max(1, (period_end - period_start).days),
        minimum=minimum,
    )
    if semantic_status != "available":
        semantic.update(
            {
                "semantic_analysis_status": semantic_status,
                "semantic_analysis_note": (
                    f"Topic intelligence requires at least {minimum} analyzed comments, "
                    f"{perception_minimum} qualifying Perceptions, and {participant_minimum} unique participants under the Topic."
                ),
            }
        )

    perception_segments = [
        {
            "perception_id": perception_id,
            "sample_size": len(values),
            "topic_name": topic_name,
        }
        for perception_id, values in sorted(
            qualifying.items(), key=lambda item: len(item[1]), reverse=True
        )
    ]

    perspectives = (
        aggregate_professional_geographic_semantics(
            participant_rows,
            minimum=minimum,
            participant_minimum=participant_minimum,
        )
        if semantic_status == "available"
        else {
            "cross_analysis_status": "insufficient_sample",
            "cross_analysis_sample_minimum": minimum,
            "cross_analysis_participant_minimum": participant_minimum,
            "cross_analysis_comment_count": analyzed_count,
            "cross_analysis_note": "Professional and geographic topic perspectives are withheld until the Topic evidence and participant privacy thresholds are met.",
            "professional_semantic_segments": [],
            "geographic_semantic_segments": [],
            "professional_geographic_segments": [],
        }
    )

    convergence_divergence = (
        analyze_cross_lens_divergence(
            professional_segments=perspectives["professional_semantic_segments"],
            geographic_segments=perspectives["geographic_semantic_segments"],
            cross_lens_segments=perspectives["professional_geographic_segments"],
            minimum=minimum,
        )
        if semantic_status == "available"
        else {
            "status": "insufficient_comparison",
            "sample_minimum": minimum,
            "convergence": [],
            "divergence": [],
            "note": "Convergence and divergence comparisons are withheld until Topic perspectives qualify.",
        }
    )

    buckets: list[dict[str, Any]] = []
    cursor = period_start
    while cursor < period_end:
        end = min(cursor + timedelta(days=TOPIC_BUCKET_DAYS), period_end)
        bucket_rows = [
            row for row, _pid, created_at in rows if cursor <= created_at < end
        ]
        available = len(bucket_rows) >= minimum
        buckets.append(
            {
                "period_start": cursor,
                "period_end": end,
                "sample_size": len(bucket_rows),
                "status": "available" if available else "insufficient_sample",
                "sentiment_distribution": (
                    _dist([r.sentiment for r in bucket_rows]) if available else []
                ),
                "stance_distribution": (
                    _dist([r.stance for r in bucket_rows]) if available else []
                ),
                "top_themes": _themes(bucket_rows) if available else [],
                "question_count": (
                    sum(1 for r in bucket_rows if r.is_question) if available else 0
                ),
                "quality_score": _quality(bucket_rows) if available else None,
            }
        )
        cursor = end

    qualifying_buckets = [b for b in buckets if b["status"] == "available"]

    patterns: list[dict[str, Any]] = []
    if semantic_status == "available":
        distributions = semantic["sentiment_distribution"]
        if distributions:
            dominant = distributions[0]
            patterns.append(
                {
                    "label": "Dominant observed sentiment",
                    "description": f"{dominant['label']} is the leading observed sentiment across qualifying responses under this Topic.",
                    "sample_size": dominant["comments"],
                    "evidence_type": "topic_semantic_distribution",
                    "limitations": [
                        "Observed sentiment describes analyzed responses and is not a population estimate."
                    ],
                }
            )
        if semantic["top_themes"]:
            theme = semantic["top_themes"][0]
            patterns.append(
                {
                    "label": "Recurring Topic theme",
                    "description": f"'{theme['theme']}' is the most frequent analyzed theme across the Topic's qualifying responses.",
                    "sample_size": theme["comments"],
                    "evidence_type": "topic_theme_distribution",
                    "limitations": [
                        "Theme frequency does not establish causation, importance, or representativeness."
                    ],
                }
            )
    if semantic_status == "available" and qualifying_count >= perception_minimum:
        patterns.append(
            {
                "label": "Multi-Perception Topic evidence",
                "description": f"The Topic contains {qualifying_count} Perceptions that independently meet the {minimum}-comment analytical threshold.",
                "sample_size": sum(len(values) for values in qualifying.values()),
                "evidence_type": "topic_perception_breadth",
                "limitations": [
                    "Qualifying Perceptions are not necessarily representative of all activity under the Topic."
                ],
            }
        )
    if len(qualifying_buckets) >= 2:
        first = qualifying_buckets[0]
        last = qualifying_buckets[-1]
        first_stance = (
            first["stance_distribution"][0]["label"]
            if first["stance_distribution"]
            else None
        )
        last_stance = (
            last["stance_distribution"][0]["label"]
            if last["stance_distribution"]
            else None
        )
        if first_stance and last_stance and first_stance != last_stance:
            patterns.append(
                {
                    "label": "Observed Topic stance change",
                    "description": "The leading observed stance differs between qualifying Topic time windows.",
                    "sample_size": min(first["sample_size"], last["sample_size"]),
                    "evidence_type": "topic_temporal_comparison",
                    "limitations": [
                        "Temporal change does not establish causation or a durable change in wider public opinion."
                    ],
                }
            )

    # Signals are patterns promoted to a higher-confidence status once the
    # underlying evidence also clears quality and freshness governance, not
    # merely the sample threshold that qualifies a pattern.
    signals: list[dict[str, Any]] = []
    if evidence_governance["signals_eligible"]:
        for pattern in patterns:
            signals.append(
                {
                    "label": pattern["label"],
                    "description": pattern["description"],
                    "status": "observed_signal",
                    "sample_size": pattern["sample_size"],
                    "evidence_type": pattern["evidence_type"],
                    "limitations": pattern["limitations"],
                }
            )

    # Free intelligence is intentionally bounded; full topic perspectives and
    # temporal evidence remain available only to entitled viewers.
    if access_tier == "free_teaser":
        patterns = patterns[:1]
        signals = []
        convergence_divergence = {
            "status": "insufficient_comparison",
            "sample_minimum": minimum,
            "convergence": [],
            "divergence": [],
            "note": "Subscribe to unlock Topic convergence and divergence comparisons.",
        }
        perspectives = {
            "cross_analysis_status": "insufficient_sample",
            "cross_analysis_sample_minimum": minimum,
            "cross_analysis_comment_count": analyzed_count,
            "cross_analysis_note": "Subscribe to unlock professional, geographic, and deeper Topic Intelligence perspectives.",
            "professional_semantic_segments": [],
            "geographic_semantic_segments": [],
            "professional_geographic_segments": [],
        }
        buckets = []

    quality = (
        _quality([row for row, _pid, _created_at in rows])
        if semantic_status == "available"
        else None
    )
    limitations = [
        "Topic Intelligence aggregates analyzed responses across multiple Perceptions under one Topic.",
        "A Topic-level observation does not imply that every Perception under the Topic has the same response pattern.",
        "Pending and failed semantic analyses are excluded from evidence-backed intelligence.",
        "A minimum sample of five analyzed comments is required; Topic breadth also requires two qualifying Perceptions and at least five unique participants before Topic-wide semantic conclusions qualify.",
        "Individual participant identities and city-level aggregate intelligence are not exposed.",
        "Observational patterns do not establish causation, prediction, or population representativeness.",
    ]
    provenance = {
        "trace_id": _trace_id(topic_id, period_start, period_end),
        "evidence_chain": [
            "human_responses",
            "comment_intelligence",
            "topic_aggregation",
        ],
        "source": "topic_intelligence",
        "evidence_types": ["comment_intelligence", "topic_perception_breadth"],
        "sample_size": analyzed_count,
        "period_start": period_start,
        "period_end": period_end,
        "scope": "topic_intelligence",
        "viewer_lens": "observer",
        "quality_score": quality,
        "qualification": semantic_status,
        "limitations": limitations,
    }
    decision_status = "available" if patterns else "insufficient_sample"
    decision = {
        "intent": decision_intent,
        "status": decision_status,
        "summary": (
            f"Topic Intelligence provides an evidence-bounded view of observed responses across {qualifying_count} qualifying Perceptions."
            if decision_status == "available"
            else "There is not enough qualifying Topic evidence to provide decision-oriented observations."
        ),
        "evidence_invariant": "Decision framing does not change the underlying samples, measurements, periods, or cohort definitions.",
        "guardrail": "Use Topic Intelligence as structured observational evidence, not as causal proof, prediction, or a population-wide estimate.",
        "limitations": limitations,
    }

    return {
        "schema_version": TOPIC_INTELLIGENCE_SCHEMA_VERSION,
        "context": {
            "schema_version": TOPIC_INTELLIGENCE_SCHEMA_VERSION,
            "topic_id": topic_id,
            "topic_name": topic_name,
            "period_start": period_start,
            "period_end": period_end,
            "period_days": max(1, (period_end - period_start).days),
            "scope": "topic_intelligence",
            "viewer_lens": "observer",
            "access_tier": access_tier,
            "upgrade_available": upgrade_available,
            "upgrade_message": upgrade_message,
        },
        "measurements": {
            "perceptions": {
                "value": len(by_perception),
                "available": True,
                "description": "Active Perceptions with analyzed response evidence under this Topic in the selected period.",
            },
            "qualifying_perceptions": {
                "value": qualifying_count,
                "available": True,
                "description": f"Perceptions with at least {minimum} analyzed comments.",
            },
            "analyzed_comments": {
                "value": analyzed_count,
                "available": True,
                "description": "Analyzed comments eligible for Topic aggregation.",
            },
            "unique_participants": {
                "value": (
                    unique_participants
                    if unique_participants >= participant_minimum
                    else None
                ),
                "available": unique_participants >= participant_minimum
                and semantic_status == "available",
                "description": (
                    "Unique active commenters represented in analyzed Topic evidence; identities are never exposed."
                    if unique_participants >= participant_minimum
                    and semantic_status == "available"
                    else f"Suppressed until at least {participant_minimum} unique participants qualify."
                ),
            },
        },
        "perceptions": perception_segments,
        "semantic": {
            "status": semantic_status,
            "note": semantic["semantic_analysis_note"],
            "sample_minimum": minimum,
            "perception_minimum": perception_minimum,
            "participant_minimum": participant_minimum,
            "analyzed_comment_count": analyzed_count,
            "qualifying_perception_count": qualifying_count,
            "quality_score": quality,
            "sentiment_distribution": (
                semantic["sentiment_distribution"]
                if semantic_status == "available"
                else []
            ),
            "stance_distribution": (
                semantic["stance_distribution"]
                if semantic_status == "available"
                else []
            ),
            "top_themes": (
                semantic["top_themes"] if semantic_status == "available" else []
            ),
            "question_count": (
                semantic["question_count"] if semantic_status == "available" else 0
            ),
            "concern_themes": (
                semantic["concern_themes"] if semantic_status == "available" else []
            ),
            "agreement_themes": (
                semantic["agreement_themes"] if semantic_status == "available" else []
            ),
            "disagreement_themes": (
                semantic["disagreement_themes"]
                if semantic_status == "available"
                else []
            ),
        },
        "perspectives": {
            "status": (
                "available"
                if perspectives["professional_semantic_segments"]
                or perspectives["geographic_semantic_segments"]
                else "insufficient_segments"
            ),
            "sample_minimum": minimum,
            "participant_minimum": participant_minimum,
            "analyzed_comment_count": analyzed_count,
            "professional": perspectives["professional_semantic_segments"],
            "geographic": perspectives["geographic_semantic_segments"],
            "professional_geographic": perspectives["professional_geographic_segments"],
            "note": perspectives["cross_analysis_note"],
        },
        "temporal": {
            "bucket_days": TOPIC_BUCKET_DAYS,
            "qualifying_bucket_count": len(qualifying_buckets),
            "buckets": buckets,
            "status": "available" if qualifying_buckets else "insufficient_sample",
            "note": f"Only {TOPIC_BUCKET_DAYS}-day Topic windows with at least {minimum} analyzed comments are shown as evidence.",
        },
        "patterns": patterns,
        "signals": signals,
        "convergence_divergence": convergence_divergence,
        "decision_context": decision,
        "provenance": provenance,
        "quality": quality_report,
        "freshness": freshness,
        "evidence_governance": evidence_governance,
        "semantic_model_governance": semantic_model_governance,
        "limitations": limitations,
    }
