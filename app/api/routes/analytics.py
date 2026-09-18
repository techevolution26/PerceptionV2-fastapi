from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import sqrt
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlalchemy import distinct, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.deps import CurrentUser, DbSession
from app.models.models import (
    AnalyticsTopic,
    Comment,
    CommentIntelligence,
    Like,
    Perception,
    PerceptionInteraction,
    PerceptionModeration,
    Topic,
    User,
)
from app.schemas.business import (
    AnalyticsEventRequest,
    AnalyticsGeoOut,
    AnalyticsInsightOut,
    AnalyticsOpportunityOut,
    AnalyticsOverviewOut,
    AnalyticsRelationshipOut,
    AnalyticsGeoTopicOut,
    AnalyticsTopicOut,
    AnalyticsTrendPoint,
)
from app.services.subscriptions import (
    get_current_subscription,
    require_analytics_access,
)
from app.services.comment_cross_analysis import (
    aggregate_professional_geographic_semantics,
)
from app.services.perception_intelligence import (
    MINIMUM_SAMPLE,
    orchestrate_perception_intelligence,
)
from app.services.decision_intelligence import build_decision_intelligence
from app.services.investigation_paths import build_investigation_paths
from app.schemas.perception_intelligence import PerceptionIntelligence
from app.services.temporal_intelligence import build_temporal_intelligence
from app.services.profile_intelligence import (
    PROFILE_WINDOW_DAYS,
    build_profile_intelligence,
)
from app.services.intelligence_freshness import (
    assess_intelligence_freshness,
    assess_topic_freshness,
)
from app.services.intelligence_quality import (
    assess_intelligence_quality,
    assess_topic_quality,
)
from app.services.evidence_governance import assess_evidence_governance
from app.services.semantic_model_governance import assess_semantic_model_governance
from app.schemas.profile_intelligence import ProfileIntelligence
from app.schemas.comparative_intelligence import ComparativeIntelligence
from app.services.comparative_intelligence import (
    COMPARISON_LIMIT,
    build_comparative_intelligence,
)
from app.schemas.topic_intelligence import TopicIntelligence
from app.services.topic_intelligence import (
    build_topic_intelligence,
    TOPIC_SAMPLE_MINIMUM,
)
from app.services.comment_intelligence import (
    get_comment_intelligence_participant_rows,
    get_comment_intelligence_rows,
    get_comment_intelligence_temporal_rows,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _strength(interactions: int, perceptions: int) -> float:
    return round(interactions / perceptions, 2) if perceptions else 0.0


def _growth(current: int, previous: int) -> float:
    if previous <= 0:
        return 1.0 if current > 0 else 0.0
    return round((current - previous) / previous, 3)


def _momentum(growth: float) -> str:
    if growth >= 0.20:
        return "rising"
    if growth <= -0.20:
        return "declining"
    return "stable"


def _evidence_level(sample_size: int) -> str:
    if sample_size >= 1000:
        return "strong"
    if sample_size >= 250:
        return "moderate"
    if sample_size >= 50:
        return "early"
    return "insufficient"


def _signal_score(
    *, perceptions: int, growth: float, engagement_rate: float, unique_participants: int
) -> float:
    """A bounded prioritisation score, not statistical confidence or probability."""
    if perceptions <= 0:
        return 0.0
    volume = min(1.0, sqrt(perceptions) / sqrt(1000))
    growth_component = min(1.0, max(0.0, growth + 1.0) / 2.0)
    engagement_component = min(1.0, engagement_rate / 10.0)
    diversity_component = min(1.0, unique_participants / perceptions)
    return round(
        100
        * (
            0.35 * volume
            + 0.30 * growth_component
            + 0.25 * engagement_component
            + 0.10 * diversity_component
        ),
        1,
    )


def _anomaly_label(current: int, baseline: float) -> str:
    if baseline <= 0:
        return "new"
    ratio = current / baseline
    if ratio >= 2.0:
        return "spike"
    if ratio <= 0.5:
        return "drop"
    return "normal"


async def _topic_scope(db: DbSession, user_id: int, max_topics: int) -> set[int] | None:
    result = await db.execute(
        select(AnalyticsTopic.topic_id)
        .where(AnalyticsTopic.user_id == user_id)
        .order_by(AnalyticsTopic.created_at)
        .limit(max_topics)
    )
    selected = set(result.scalars().all())
    return selected or None


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def record_interaction(
    payload: AnalyticsEventRequest, current_user: CurrentUser, db: DbSession
):
    event_type = payload.event_type.upper()
    if event_type not in {"VIEW", "SHARE"}:
        raise HTTPException(
            status_code=422, detail="Supported analytics events: ['SHARE', 'VIEW']"
        )

    exists = await db.execute(
        select(Perception.id).where(Perception.id == payload.perception_id)
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Perception not found")

    day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    statement = (
        pg_insert(PerceptionInteraction)
        .values(
            actor_user_id=current_user.id,
            perception_id=payload.perception_id,
            event_type=event_type,
            occurred_on=day,
        )
        .on_conflict_do_nothing(
            index_elements=[
                PerceptionInteraction.actor_user_id,
                PerceptionInteraction.perception_id,
                PerceptionInteraction.event_type,
                PerceptionInteraction.occurred_on,
            ]
        )
    )
    result = await db.execute(statement)
    await db.commit()

    return {
        "recorded": result.rowcount == 1,
        "event_type": event_type,
    }


@router.get("/overview", response_model=AnalyticsOverviewOut)
async def analytics_overview(current_user: CurrentUser, db: DbSession, days: int = 30):
    sub = await require_analytics_access(db, current_user.id)
    days = max(7, min(days, 365))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    topic_scope = await _topic_scope(db, current_user.id, sub.plan.max_topics)
    current_filters = [
        Perception.user_id == current_user.id,
        Perception.created_at >= since,
    ]
    previous_filters = [
        Perception.user_id == current_user.id,
        Perception.created_at >= previous_since,
        Perception.created_at < since,
    ]
    if topic_scope:
        current_filters.append(Perception.topic_id.in_(topic_scope))
        previous_filters.append(Perception.topic_id.in_(topic_scope))

    current_rows = (
        await db.execute(
            select(
                Perception.id,
                Perception.topic_id,
                User.id,
                User.country_code,
                Perception.created_at,
            )
            .join(User, User.id == Perception.user_id)
            .where(*current_filters)
        )
    ).all()
    previous_rows = (
        await db.execute(
            select(Perception.topic_id, func.count(Perception.id))
            .where(*previous_filters)
            .group_by(Perception.topic_id)
        )
    ).all()
    previous_counts = {topic_id: count for topic_id, count in previous_rows}

    ids = [row.id for row in current_rows]
    topic_stats = defaultdict(
        lambda: {
            "perceptions": 0,
            "likes": 0,
            "comments": 0,
            "views": 0,
            "shares": 0,
            "participants": set(),
        }
    )
    geo_stats = defaultdict(lambda: {"perceptions": 0, "interactions": 0})
    trend_stats = defaultdict(lambda: {"perceptions": 0, "interactions": 0})
    participants = {row[2] for row in current_rows}

    for row in current_rows:
        stat = topic_stats[row.topic_id]
        stat["perceptions"] += 1
        country = (row.country_code or "UNKNOWN").upper()
        geo_stats[country]["perceptions"] += 1
        trend_stats[row.created_at.date().isoformat()]["perceptions"] += 1

    if ids:
        like_rows = (
            await db.execute(
                select(
                    Perception.topic_id,
                    func.count(Like.id),
                    func.count(distinct(Like.user_id)),
                )
                .join(Like, Like.perception_id == Perception.id)
                .where(Perception.id.in_(ids))
                .group_by(Perception.topic_id)
            )
        ).all()
        for topic_id, count, _unique_users in like_rows:
            topic_stats[topic_id]["likes"] = count

        comment_rows = (
            await db.execute(
                select(
                    Perception.topic_id,
                    func.count(Comment.id),
                    func.count(distinct(Comment.user_id)),
                )
                .join(Comment, Comment.perception_id == Perception.id)
                .where(Perception.id.in_(ids))
                .group_by(Perception.topic_id)
            )
        ).all()
        for topic_id, count, _unique_users in comment_rows:
            topic_stats[topic_id]["comments"] = count

        participant_rows = await db.execute(
            select(Like.user_id)
            .where(Like.perception_id.in_(ids))
            .union(select(Comment.user_id).where(Comment.perception_id.in_(ids)))
        )
        interaction_users = participant_rows.scalars().all()
        participants.update(interaction_users)
        for user_id in interaction_users:
            # Topic membership is resolved below from interaction rows; the global participant set is still exact.
            pass

        event_rows = (
            await db.execute(
                select(
                    Perception.topic_id,
                    PerceptionInteraction.event_type,
                    func.count(PerceptionInteraction.id),
                )
                .join(
                    PerceptionInteraction,
                    PerceptionInteraction.perception_id == Perception.id,
                )
                .where(
                    Perception.id.in_(ids), PerceptionInteraction.created_at >= since
                )
                .group_by(Perception.topic_id, PerceptionInteraction.event_type)
            )
        ).all()
        for topic_id, event_type, count in event_rows:
            if event_type == "VIEW":
                topic_stats[topic_id]["views"] = count
            elif event_type == "SHARE":
                topic_stats[topic_id]["shares"] = count

        event_participant_rows = await db.execute(
            select(Perception.topic_id, PerceptionInteraction.actor_user_id)
            .join(
                PerceptionInteraction,
                PerceptionInteraction.perception_id == Perception.id,
            )
            .where(Perception.id.in_(ids), PerceptionInteraction.created_at >= since)
            .distinct()
        )
        for topic_id, actor_id in event_participant_rows.all():
            topic_stats[topic_id]["participants"].add(actor_id)
            participants.add(actor_id)

        like_participant_rows = await db.execute(
            select(Perception.topic_id, Like.user_id)
            .join(Like, Like.perception_id == Perception.id)
            .where(Perception.id.in_(ids))
            .distinct()
        )
        for topic_id, actor_id in like_participant_rows.all():
            topic_stats[topic_id]["participants"].add(actor_id)

        comment_participant_rows = await db.execute(
            select(Perception.topic_id, Comment.user_id)
            .join(Comment, Comment.perception_id == Perception.id)
            .where(Perception.id.in_(ids))
            .distinct()
        )
        for topic_id, actor_id in comment_participant_rows.all():
            topic_stats[topic_id]["participants"].add(actor_id)

        event_trend = (
            await db.execute(
                select(
                    func.date(PerceptionInteraction.created_at),
                    func.count(PerceptionInteraction.id),
                )
                .where(
                    PerceptionInteraction.perception_id.in_(ids),
                    PerceptionInteraction.created_at >= since,
                )
                .group_by(func.date(PerceptionInteraction.created_at))
            )
        ).all()
        for date_value, count in event_trend:
            trend_stats[str(date_value)]["interactions"] += count

        geo_like_rows = (
            await db.execute(
                select(User.country_code, func.count(Like.id))
                .join(Perception, Perception.user_id == User.id)
                .join(Like, Like.perception_id == Perception.id)
                .where(Perception.id.in_(ids))
                .group_by(User.country_code)
            )
        ).all()
        for country, count in geo_like_rows:
            geo_stats[(country or "UNKNOWN").upper()]["interactions"] += count

        geo_comment_rows = (
            await db.execute(
                select(User.country_code, func.count(Comment.id))
                .join(Perception, Perception.user_id == User.id)
                .join(Comment, Comment.perception_id == Perception.id)
                .where(Perception.id.in_(ids))
                .group_by(User.country_code)
            )
        ).all()
        for country, count in geo_comment_rows:
            geo_stats[(country or "UNKNOWN").upper()]["interactions"] += count

        geo_event_rows = (
            await db.execute(
                select(User.country_code, func.count(PerceptionInteraction.id))
                .join(Perception, Perception.user_id == User.id)
                .join(
                    PerceptionInteraction,
                    PerceptionInteraction.perception_id == Perception.id,
                )
                .where(
                    Perception.id.in_(ids), PerceptionInteraction.created_at >= since
                )
                .group_by(User.country_code)
            )
        ).all()
        for country, count in geo_event_rows:
            geo_stats[(country or "UNKNOWN").upper()]["interactions"] += count

    topic_names = dict((await db.execute(select(Topic.id, Topic.name))).all())
    topics: list[AnalyticsTopicOut] = []
    for topic_id, stat in topic_stats.items():
        interactions = stat["likes"] + stat["comments"] + stat["views"] + stat["shares"]
        perceptions = stat["perceptions"]
        growth = _growth(perceptions, previous_counts.get(topic_id, 0))
        topics.append(
            AnalyticsTopicOut(
                topic_id=topic_id or 0,
                topic_name=topic_names.get(topic_id, "Uncategorized"),
                perception_count=perceptions,
                likes=stat["likes"],
                comments=stat["comments"],
                views=stat["views"],
                shares=stat["shares"],
                interactions=interactions,
                engagement_rate=(
                    round(interactions / perceptions, 2) if perceptions else 0.0
                ),
                signal_strength=_strength(interactions, perceptions),
                signal_score=_signal_score(
                    perceptions=perceptions,
                    growth=growth,
                    engagement_rate=interactions / perceptions if perceptions else 0.0,
                    unique_participants=len(stat["participants"]),
                ),
                unique_participants=len(stat["participants"]),
                previous_perception_count=previous_counts.get(topic_id, 0),
                growth_rate=growth,
                momentum=_momentum(growth),
                evidence_level=_evidence_level(perceptions),
            )
        )

    topics.sort(
        key=lambda item: (
            item.topic_id == current_user.primary_analytics_topic_id,
            item.signal_score,
            item.perception_count,
        ),
        reverse=True,
    )
    topics = topics[: max(1, sub.plan.max_topics)]

    total_perceptions = sum(t.perception_count for t in topics)
    total_likes = sum(t.likes for t in topics)
    total_comments = sum(t.comments for t in topics)
    total_views = sum(t.views for t in topics)
    total_shares = sum(t.shares for t in topics)
    total_interactions = total_likes + total_comments + total_views + total_shares

    geography = [
        AnalyticsGeoOut(
            country_code=country,
            perception_count=data["perceptions"],
            interactions=data["interactions"],
            engagement_rate=(
                round(data["interactions"] / data["perceptions"], 2)
                if data["perceptions"]
                else 0.0
            ),
            share_of_perceptions=(
                round(data["perceptions"] / total_perceptions, 3)
                if total_perceptions
                else 0.0
            ),
        )
        for country, data in sorted(
            geo_stats.items(), key=lambda item: item[1]["perceptions"], reverse=True
        )
    ]

    trend = []
    for offset in range(days):
        date_value = (since + timedelta(days=offset)).date().isoformat()
        data = trend_stats[date_value]
        trend.append(
            AnalyticsTrendPoint(
                date=date_value,
                perceptions=data["perceptions"],
                interactions=data["interactions"],
            )
        )

    # Baseline is the mean daily perception volume over the previous equal-length period.
    previous_total = sum(previous_counts.values())
    baseline_daily = previous_total / days if days else 0.0
    recent_daily = total_perceptions / days if days else 0.0
    anomaly = _anomaly_label(round(recent_daily), baseline_daily)

    opportunities: list[AnalyticsOpportunityOut] = []
    for topic in sorted(
        topics, key=lambda item: (item.signal_score, item.growth_rate), reverse=True
    ):
        if topic.perception_count < 10:
            continue
        if topic.growth_rate >= 0.20 or topic.signal_strength >= 3.0:
            if topic.growth_rate >= 0.20 and topic.signal_strength >= 1.5:
                reason = "Growing volume combined with meaningful interaction activity."
            elif topic.growth_rate >= 0.20:
                reason = "Perception volume is increasing versus the prior period."
            else:
                reason = "Interaction activity is high relative to perception volume."
            opportunities.append(
                AnalyticsOpportunityOut(
                    topic_id=topic.topic_id,
                    topic_name=topic.topic_name,
                    reason=reason,
                    signal_strength=topic.signal_strength,
                    signal_score=topic.signal_score,
                    growth_rate=topic.growth_rate,
                    sample_size=topic.perception_count,
                    unique_participants=topic.unique_participants,
                    evidence_level=topic.evidence_level,
                )
            )
        if len(opportunities) == 5:
            break

    primary_topic = next(
        (t for t in topics if t.topic_id == current_user.primary_analytics_topic_id),
        None,
    )
    strongest_topic = max(topics, key=lambda item: item.signal_score, default=None)
    emerging_topic = max(
        (t for t in topics if t.perception_count >= 10),
        key=lambda item: (item.growth_rate, item.signal_score),
        default=None,
    )

    insights: list[AnalyticsInsightOut] = []
    if strongest_topic:
        insights.append(
            AnalyticsInsightOut(
                kind="strength",
                title=f"{strongest_topic.topic_name} has the strongest composite signal",
                detail=f"Its prioritisation score is {strongest_topic.signal_score}/100 across {strongest_topic.perception_count} perceptions and {strongest_topic.unique_participants} participants.",
                confidence="descriptive",
            )
        )
    if emerging_topic and emerging_topic.growth_rate >= 0.20:
        insights.append(
            AnalyticsInsightOut(
                kind="trend",
                title=f"{emerging_topic.topic_name} is gaining momentum",
                detail=f"Perception volume is {emerging_topic.growth_rate:.0%} higher than the preceding period.",
                confidence=emerging_topic.evidence_level,
            )
        )
    if geography and total_perceptions:
        top_geo = geography[0]
        if top_geo.share_of_perceptions >= 0.50:
            insights.append(
                AnalyticsInsightOut(
                    kind="geography",
                    title=f"Activity is concentrated in {top_geo.country_code}",
                    detail=f"{top_geo.share_of_perceptions:.0%} of perceptions originate from this country in the selected sample.",
                    confidence="descriptive",
                )
            )
    if anomaly != "normal":
        insights.append(
            AnalyticsInsightOut(
                kind="anomaly",
                title=f"Overall activity shows a {anomaly}",
                detail=f"Average daily perception volume is {recent_daily:.1f} versus {baseline_daily:.1f} in the preceding period.",
                confidence="screening",
            )
        )

    methodology = [
        "The composite signal score prioritises volume, period growth, engagement and participant diversity; it is not a probability or confidence interval.",
        "Growth compares the selected period with the immediately preceding period of equal length.",
        "Anomaly screening compares average daily perception volume with the preceding period; it is a screening heuristic, not a statistical test.",
        "Evidence level is a sample-size heuristic: early at 50+, moderate at 250+, strong at 1,000+ observations.",
        "Geographic results describe the countries represented by perception authors; they are not population-representative estimates.",
        "Engagement includes likes, comments, and deduplicated view/share events recorded by the platform.",
        "Opportunity signals identify patterns worth investigating. They are not proof of market demand, causation, or scientific findings.",
        "Scientific claims require independent study design, representative sampling where appropriate, controls, statistical testing and domain review.",
    ]

    return AnalyticsOverviewOut(
        period_days=days,
        sample_size=total_perceptions,
        unique_participants=len(participants),
        total_perceptions=total_perceptions,
        total_likes=total_likes,
        total_comments=total_comments,
        total_views=total_views,
        total_shares=total_shares,
        total_interactions=total_interactions,
        engagement_rate=(
            round(total_interactions / total_perceptions, 2)
            if total_perceptions
            else 0.0
        ),
        geographic_coverage=len([g for g in geography if g.country_code != "UNKNOWN"]),
        primary_topic_id=(
            primary_topic.topic_id
            if primary_topic
            else current_user.primary_analytics_topic_id
        ),
        primary_topic_name=primary_topic.topic_name if primary_topic else None,
        strongest_topic=strongest_topic,
        emerging_topic=emerging_topic,
        activity_baseline_daily=round(baseline_daily, 2),
        activity_current_daily=round(recent_daily, 2),
        activity_anomaly=anomaly,
        insights=insights,
        topics=topics,
        geography=geography,
        trend=trend,
        opportunities=opportunities,
        methodology=methodology,
    )


@router.get("/intelligence", response_model=dict)
async def analytics_intelligence(
    current_user: CurrentUser, db: DbSession, days: int = 30
):
    """Cross-topic and geographic relationships for decision-support analytics.

    Relationships are descriptive associations based on shared authors and
    geography. They are not causal relationships or proof of market demand.
    """
    sub = await require_analytics_access(db, current_user.id)
    days = max(7, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    topic_scope = await _topic_scope(db, current_user.id, sub.plan.max_topics)

    filters = [
        Perception.user_id == current_user.id,
        Perception.created_at >= since,
        Perception.topic_id.is_not(None),
    ]
    if topic_scope:
        filters.append(Perception.topic_id.in_(topic_scope))

    rows = (
        await db.execute(
            select(Perception.user_id, Perception.topic_id, User.country_code)
            .join(User, User.id == Perception.user_id)
            .where(*filters)
        )
    ).all()

    topic_names = dict((await db.execute(select(Topic.id, Topic.name))).all())
    users_by_topic: dict[int, set[int]] = defaultdict(set)
    geo_topic: dict[tuple[int, str], int] = defaultdict(int)
    topic_totals: dict[int, int] = defaultdict(int)
    for user_id, topic_id, country in rows:
        topic = int(topic_id)
        users_by_topic[topic].add(int(user_id))
        code = (country or "UNKNOWN").upper()
        geo_topic[(topic, code)] += 1
        topic_totals[topic] += 1

    relationships: list[AnalyticsRelationshipOut] = []
    topic_ids = sorted(users_by_topic)
    for index, topic_a in enumerate(topic_ids):
        for topic_b in topic_ids[index + 1 :]:
            a_users = users_by_topic[topic_a]
            b_users = users_by_topic[topic_b]
            shared = len(a_users & b_users)
            union = len(a_users | b_users)
            if shared == 0 or union == 0:
                continue
            jaccard = shared / union
            # Bounded association score: overlap plus shared participant count.
            strength = round(100 * min(1.0, jaccard * 2.0) * min(1.0, shared / 50), 1)
            relationships.append(
                AnalyticsRelationshipOut(
                    topic_a_id=topic_a,
                    topic_a_name=topic_names.get(topic_a, "Uncategorized"),
                    topic_b_id=topic_b,
                    topic_b_name=topic_names.get(topic_b, "Uncategorized"),
                    shared_participants=shared,
                    participant_overlap=round(jaccard, 3),
                    relationship_strength=strength,
                    evidence_level=_evidence_level(shared),
                )
            )

    relationships.sort(
        key=lambda item: (item.relationship_strength, item.shared_participants),
        reverse=True,
    )
    relationships = relationships[:20]

    geo_signals: list[AnalyticsGeoTopicOut] = []
    for (topic_id, country), count in geo_topic.items():
        if count < 3:
            continue
        share = count / topic_totals[topic_id]
        score = round(100 * min(1.0, share * 1.5) * min(1.0, count / 100), 1)
        geo_signals.append(
            AnalyticsGeoTopicOut(
                topic_id=topic_id,
                topic_name=topic_names.get(topic_id, "Uncategorized"),
                country_code=country,
                perception_count=count,
                share_of_topic=round(share, 3),
                signal_score=score,
                evidence_level=_evidence_level(count),
            )
        )
    geo_signals.sort(
        key=lambda item: (item.signal_score, item.perception_count), reverse=True
    )
    geo_signals = geo_signals[:30]

    return {
        "period_days": days,
        "relationships": relationships,
        "geographic_topic_signals": geo_signals,
        "methodology": [
            "Topic relationships measure overlap in people who authored perceptions across two topics during the selected period.",
            "Participant overlap is Jaccard similarity: shared participants divided by the union of participants.",
            "Geographic topic signals describe where perception authors are represented; they are not population-representative demand estimates.",
            "Relationships are associative and descriptive. They do not establish causation or prove that one topic drives another.",
            "Low-volume geographic signals are suppressed to reduce misleading conclusions from tiny samples.",
        ],
    }


@router.get("/decision", response_model=dict)
async def analytics_decision(current_user: CurrentUser, db: DbSession, days: int = 30):
    """Return an actionable decision-support lens for the user's primary professional area."""
    overview = await analytics_overview(current_user, db, days)
    primary = overview.primary_topic_name
    focus = (
        current_user.professional_focus or current_user.profession or "your focus area"
    )

    ranked = sorted(
        overview.opportunities, key=lambda item: item.signal_score, reverse=True
    )
    recommendations: list[dict[str, object]] = []
    for opportunity in ranked[:5]:
        if opportunity.evidence_level == "insufficient":
            action = "Collect more observations before making a decision."
        elif opportunity.growth_rate >= 0.20:
            action = "Investigate the drivers of this growth and validate demand independently."
        else:
            action = "Compare this signal with local context and independent evidence."
        recommendations.append(
            {
                "topic_id": opportunity.topic_id,
                "topic_name": opportunity.topic_name,
                "action": action,
                "signal_score": opportunity.signal_score,
                "evidence_level": opportunity.evidence_level,
            }
        )

    return {
        "period_days": overview.period_days,
        "lens": focus,
        "primary_topic_id": overview.primary_topic_id,
        "primary_topic_name": primary,
        "strongest_signal": (
            overview.strongest_topic.model_dump() if overview.strongest_topic else None
        ),
        "emerging_signal": (
            overview.emerging_topic.model_dump() if overview.emerging_topic else None
        ),
        "recommendations": recommendations,
        "guardrail": "These are observed signals and investigation prompts, not predictions, causal conclusions, proof of demand, or scientific findings.",
    }


@router.get("/opportunities/{topic_id}", response_model=dict)
async def analytics_opportunity_detail(
    topic_id: int, current_user: CurrentUser, db: DbSession, days: int = 30
):
    """Explain one topic signal with evidence, geography and related topics."""
    overview = await analytics_overview(current_user, db, days)
    topic = next((item for item in overview.topics if item.topic_id == topic_id), None)
    if topic is None:
        raise HTTPException(
            status_code=404, detail="Analytics topic not found in the selected period"
        )

    since = datetime.now(timezone.utc) - timedelta(days=overview.period_days)
    rows = (
        await db.execute(
            select(Perception.user_id, Perception.topic_id, User.country_code)
            .join(User, User.id == Perception.user_id)
            .where(Perception.created_at >= since, Perception.topic_id == topic_id)
        )
    ).all()
    by_country: dict[str, int] = defaultdict(int)
    participants: set[int] = set()
    for user_id, _topic_id, country in rows:
        participants.add(int(user_id))
        by_country[(country or "UNKNOWN").upper()] += 1

    related: list[dict[str, object]] = []
    for item in (await analytics_intelligence(current_user, db, overview.period_days))[
        "relationships"
    ]:
        if item.topic_a_id == topic_id:
            related.append(item.model_dump())
        elif item.topic_b_id == topic_id:
            related.append(item.model_dump())
    related.sort(key=lambda item: float(item["relationship_strength"]), reverse=True)

    geography = [
        {
            "country_code": code,
            "perception_count": count,
            "share_of_topic": round(count / len(rows), 3) if rows else 0.0,
        }
        for code, count in sorted(
            by_country.items(), key=lambda item: item[1], reverse=True
        )
    ]
    return {
        "topic": topic.model_dump(),
        "professional_lens": current_user.professional_focus or current_user.profession,
        "geography": geography[:20],
        "unique_participants": len(participants),
        "related_topics": related[:10],
        "recommended_next_step": (
            "Validate this signal with independent market, field, or domain evidence before acting."
            if topic.evidence_level != "strong"
            else "Use this as a prioritisation input, then validate the underlying hypothesis independently."
        ),
        "guardrail": "Association and observed activity do not establish causation, population demand, or scientific validity.",
    }


@router.get("/perceptions/{perception_id}", response_model=PerceptionIntelligence)
async def perception_analytics(
    perception_id: int,
    current_user: CurrentUser,
    db: DbSession,
    days: int = 30,
    decision_intent: Literal[
        "research",
        "business",
        "policy",
        "journalism",
        "education",
        "product",
        "professional",
        "general_exploration",
    ] = "general_exploration",
):
    days = max(7, min(days, 365))
    p = await db.scalar(
        select(Perception)
        .join(User, User.id == Perception.user_id)
        .options(selectinload(Perception.user), selectinload(Perception.topic))
        .where(Perception.id == perception_id, User.is_active.is_(True))
    )
    if p is None:
        raise HTTPException(404, "Perception not found")

    is_author = p.user_id == current_user.id
    current_subscription = await get_current_subscription(db, current_user.id)
    has_analytics_plan = bool(
        current_subscription
        and current_subscription.plan
        and current_subscription.plan.analytics_enabled
    )

    now = datetime.now(timezone.utc)
    period_end = now
    since = max(p.created_at, now - timedelta(days=days))

    likes = int(
        await db.scalar(
            select(func.count(Like.id)).where(
                Like.perception_id == p.id, Like.created_at >= since
            )
        )
        or 0
    )
    comments = int(
        await db.scalar(
            select(func.count(Comment.id)).where(
                Comment.perception_id == p.id, Comment.created_at >= since
            )
        )
        or 0
    )
    views = int(
        await db.scalar(
            select(func.count(PerceptionInteraction.id)).where(
                PerceptionInteraction.perception_id == p.id,
                PerceptionInteraction.event_type == "VIEW",
                PerceptionInteraction.created_at >= since,
            )
        )
        or 0
    )
    shares = int(
        await db.scalar(
            select(func.count(PerceptionInteraction.id)).where(
                PerceptionInteraction.perception_id == p.id,
                PerceptionInteraction.event_type == "SHARE",
                PerceptionInteraction.created_at >= since,
            )
        )
        or 0
    )

    # Audience perspective is conversation-derived: likes/views/shares are
    # creator measurements, but they do not make someone a conversation
    # participant. Keep the two populations separate so a perception with
    # zero comments cannot report a non-zero conversational audience.
    comment_participant_ids = set(
        (
            await db.execute(
                select(Comment.user_id).where(
                    Comment.perception_id == p.id, Comment.created_at >= since
                )
            )
        )
        .scalars()
        .all()
    )

    activity = (
        await db.execute(
            select(
                func.date(PerceptionInteraction.created_at),
                func.count(PerceptionInteraction.id),
            )
            .where(
                PerceptionInteraction.perception_id == p.id,
                PerceptionInteraction.created_at >= since,
            )
            .group_by(func.date(PerceptionInteraction.created_at))
            .order_by(func.date(PerceptionInteraction.created_at))
        )
    ).all()
    # All audience breakdowns are commenter-derived. Semantic cohorts below
    # are stricter still: they require analyzed comments.
    participants = (
        (await db.execute(select(User).where(User.id.in_(comment_participant_ids))))
        .scalars()
        .all()
        if comment_participant_ids
        else []
    )

    audience_minimum = MINIMUM_SAMPLE
    country_counts: dict[str, int] = {}
    region_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    verified_role_counts: dict[str, int] = {}
    audience_available = len(participants) >= audience_minimum
    if audience_available:
        for participant in participants:
            country = (participant.country_code or "UNKNOWN").upper()
            country_counts[country] = country_counts.get(country, 0) + 1
            region = (participant.region or "UNKNOWN").strip()
            region_key = f"{country} · {region}" if region != "UNKNOWN" else country
            region_counts[region_key] = region_counts.get(region_key, 0) + 1
            roles = participant.professional_roles or []
            if not roles and participant.profession:
                roles = [participant.profession]
            for role_code in roles[:5]:
                code = str(role_code)
                role_counts[code] = role_counts.get(code, 0) + 1
                if code in (participant.verified_professional_roles or []):
                    verified_role_counts[code] = verified_role_counts.get(code, 0) + 1

    role_label_by_code: dict[str, str] = {}
    for participant in participants:
        for code, label in zip(
            participant.professional_roles or [], participant.professional_role_labels
        ):
            role_label_by_code[str(code)] = label

    freshness = await assess_intelligence_freshness(db, p.id, since)
    quality = await assess_intelligence_quality(db, p.id, since, minimum=MINIMUM_SAMPLE)
    semantic_rows = await get_comment_intelligence_rows(db, p.id, since)
    semantic_model_governance = assess_semantic_model_governance(
        semantic_rows, minimum_version_sample=MINIMUM_SAMPLE
    )
    evidence_governance = assess_evidence_governance(
        analyzed_count=quality["analyzed_comment_count"],
        pending_count=quality["pending_comment_count"],
        failed_count=quality["failed_comment_count"],
        quality_status=quality["status"],
        quality_score=quality["quality_score"],
        freshness_status=freshness["status"],
        minimum=MINIMUM_SAMPLE,
    )
    access_tier = "full" if has_analytics_plan else "free_teaser"
    upgrade_message = (
        None
        if has_analytics_plan
        else "You are seeing a free taste of the strongest conversation intelligence. Subscribe to unlock deeper perspectives, cross-lens comparisons, temporal intelligence, and decision context."
    )

    temporal_rows = await get_comment_intelligence_temporal_rows(db, p.id, since)
    temporal = build_temporal_intelligence(
        temporal_rows, period_start=since, period_end=period_end, minimum=MINIMUM_SAMPLE
    )

    semantic_participant_rows = await get_comment_intelligence_participant_rows(
        db, p.id, since
    )
    cross_analysis = aggregate_professional_geographic_semantics(
        semantic_participant_rows, minimum=MINIMUM_SAMPLE
    )
    composed = orchestrate_perception_intelligence(
        topic_id=p.topic_id,
        topic_name=p.topic.name if p.topic else None,
        perception_id=p.id,
        period_start=since,
        period_end=period_end,
        period_days=days,
        semantic_rows=semantic_rows,
        participant_rows=semantic_participant_rows,
        cross_lens=cross_analysis,
        scope="creator_analytics" if is_author else "conversation_intelligence",
        viewer_lens="author" if is_author else "observer",
        minimum=MINIMUM_SAMPLE,
    )

    semantic_data = composed["semantic"]["semantic_evidence"]
    semantic_observed = {
        item["type"]: item["observed"] for item in semantic_data["evidence"]
    }
    semantic_available = semantic_data["evidence_status"] == "available"

    semantic = {
        "status": "available" if semantic_available else "insufficient_sample",
        "note": (
            "Aggregate semantic signals from analyzed comments."
            if semantic_available
            else f"Semantic intelligence is withheld until at least {MINIMUM_SAMPLE} comments have been analyzed."
        ),
        "sample_minimum": MINIMUM_SAMPLE,
        "analyzed_comment_count": composed["semantic"]["analyzed_comment_count"],
        "period_days": days,
        "quality_score": semantic_data["quality_score"],
        "sentiment_distribution": semantic_observed.get("sentiment_distribution", []),
        "stance_distribution": semantic_observed.get("stance_distribution", []),
        "top_themes": semantic_observed.get("top_themes", []),
        "question_count": semantic_observed.get("question_count", 0),
        "concern_themes": semantic_observed.get("concern_themes", []),
        "agreement_themes": semantic_observed.get("agreement_themes", []),
        "disagreement_themes": semantic_observed.get("disagreement_themes", []),
    }

    perspective = {
        "status": cross_analysis["cross_analysis_status"],
        "note": cross_analysis["cross_analysis_note"],
        "sample_minimum": cross_analysis["cross_analysis_sample_minimum"],
        "analyzed_comment_count": cross_analysis["cross_analysis_comment_count"],
        "professional": cross_analysis["professional_semantic_segments"],
        "geographic": cross_analysis["geographic_semantic_segments"],
        "cross_lens": cross_analysis["professional_geographic_segments"],
    }

    methodology_limits = [
        "Platform observations are not automatically population-representative.",
        "Observational patterns do not establish causation.",
        "Individual participant identities are not exposed in intelligence aggregates.",
    ]
    methodology_rules = [
        f"Semantic intelligence is suppressed below {MINIMUM_SAMPLE} analyzed comments.",
        f"Professional and geographic semantic cohorts are independently suppressed below {MINIMUM_SAMPLE} comments.",
        "Professional cohorts use primary professional identity; geography uses country and region.",
        "City-level reporting is not exposed.",
        "Creator measurements are visible only to the author; observer scope exposes conversation-level aggregates.",
        "Decision context reframes observed evidence and does not establish causation or prediction.",
    ]
    if is_author:
        methodology_rules.insert(
            0, "Creator analytics require an analytics-enabled plan."
        )

    patterns = composed["patterns"]
    signals = composed["signals"]
    if not evidence_governance["patterns_eligible"]:
        patterns = []
        signals = []
    elif not evidence_governance["signals_eligible"]:
        signals = []

    if access_tier == "free_teaser":
        patterns = patterns[:1]
        signals = signals[:1]
        perspective = {
            **perspective,
            "professional": [],
            "geographic": [],
            "cross_lens": [],
        }
        temporal = {
            **temporal,
            "buckets": [],
            "changes": [],
            "qualifying_bucket_count": 0,
        }

    try:
        decision = build_decision_intelligence(
            intent=decision_intent,
            patterns=patterns,
            signals=signals,
            cross_lens_analysis=composed["cross_lens_comparison"],
            temporal={"changes": temporal["changes"]},
            minimum=MINIMUM_SAMPLE,
        )
        investigation_paths = build_investigation_paths(
            intent=decision_intent,
            observations=decision.get("observations", []),
            minimum=MINIMUM_SAMPLE,
        )
        decision = {**decision, "investigation_paths": investigation_paths}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if access_tier == "free_teaser":
        decision = {
            **decision,
            # The API contract intentionally has only available/insufficient_sample.
            # Free-tier limitation is expressed through the summary/limitations,
            # not by inventing a third decision status.
            "status": (
                "available" if decision.get("observations") else "insufficient_sample"
            ),
            "summary": "A limited view of the strongest evidence-backed observation is available on the free plan.",
            "observations": decision.get("observations", [])[:1],
            "investigation_paths": decision.get("investigation_paths", [])[:1],
            "considerations": [],
            "guardrail": decision.get("guardrail"),
            "limitations": [
                "Subscribe to unlock deeper decision framing and comparative intelligence."
            ],
        }

    measurements = {
        "likes": {
            "value": likes,
            "available": True,
            "description": "Likes recorded during the selected period.",
        },
        "comments": {
            "value": comments,
            "available": True,
            "description": "Comments recorded during the selected period.",
        },
        "views": {
            "value": views if is_author and has_analytics_plan else None,
            "available": is_author and has_analytics_plan,
            "description": "Views recorded during the selected period; creator-only.",
        },
        "shares": {
            "value": shares if is_author and has_analytics_plan else None,
            "available": is_author and has_analytics_plan,
            "description": "Shares recorded during the selected period; creator-only.",
        },
        "engagement_rate": {
            "value": (
                (round((likes + comments + shares) / views, 4) if views else 0.0)
                if is_author and has_analytics_plan
                else None
            ),
            "available": is_author and has_analytics_plan,
            "description": "(likes + comments + shares) / views for the selected period; creator-only.",
        },
        "daily_activity": (
            [{"date": str(d), "interactions": int(c)} for d, c in activity]
            if is_author and has_analytics_plan
            else []
        ),
    }

    return PerceptionIntelligence(
        context={
            "schema_version": composed["schema_version"],
            "topic_id": p.topic_id,
            "topic_name": p.topic.name if p.topic else None,
            "perception_id": p.id,
            "period_start": since,
            "period_end": period_end,
            "period_days": days,
            "scope": "creator_analytics" if is_author else "conversation_intelligence",
            "viewer_lens": "author" if is_author else "observer",
            "author": {
                "professional_role": p.user.primary_professional_role_label
                or p.user.profession,
                "verified": p.user.verification_status == "VERIFIED"
                and bool(p.user.verified_professional_roles),
            },
            "access_tier": access_tier,
            "upgrade_available": not has_analytics_plan,
            "upgrade_message": upgrade_message,
        },
        provenance=composed["provenance"],
        freshness=freshness,
        quality=quality,
        evidence_governance=evidence_governance,
        semantic_model_governance=semantic_model_governance,
        measurements=measurements,
        audience={
            "unique_participants": len(comment_participant_ids),
            "breakdown": {
                "minimum": audience_minimum,
                "available": audience_available,
                "countries": [
                    {"country_code": code, "participants": count}
                    for code, count in sorted(
                        country_counts.items(), key=lambda item: item[1], reverse=True
                    )[:10]
                ],
                "regions": [
                    {"region": region, "participants": count}
                    for region, count in sorted(
                        region_counts.items(), key=lambda item: item[1], reverse=True
                    )[:10]
                ],
                "professional_roles": [
                    {
                        "role_code": code,
                        "role_label": role_label_by_code.get(code, code),
                        "participants": count,
                    }
                    for code, count in sorted(
                        role_counts.items(), key=lambda item: item[1], reverse=True
                    )[:10]
                ],
                "verified_professional_roles": [
                    {
                        "role_code": code,
                        "role_label": role_label_by_code.get(code, code),
                        "participants": count,
                    }
                    for code, count in sorted(
                        verified_role_counts.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:10]
                ],
            },
        },
        semantic=semantic,
        perspectives=perspective,
        cross_lens_analysis=composed["cross_lens_comparison"],
        temporal=temporal,
        patterns=patterns,
        signals=signals,
        decision_context=decision,
        methodology={
            "sample_minimum": MINIMUM_SAMPLE,
            "quality_score_definition": "Mean stored comment-intelligence quality score across analyzed comments; no score is exposed below the minimum sample.",
            "limitations": methodology_limits,
            "rules": methodology_rules,
        },
    )


@router.get("/topics/{topic_id}", response_model=TopicIntelligence)
async def topic_intelligence(
    topic_id: int,
    current_user: CurrentUser,
    db: DbSession,
    days: int = 180,
    decision_intent: Literal[
        "research",
        "business",
        "policy",
        "journalism",
        "education",
        "product",
        "professional",
        "general_exploration",
    ] = "general_exploration",
):
    """Aggregate evidence across active Perceptions belonging to one Topic."""
    days = max(30, min(days, 365))
    topic = await db.scalar(select(Topic).where(Topic.id == topic_id))
    if topic is None:
        raise HTTPException(404, "Topic not found")

    subscription = await get_current_subscription(db, current_user.id)
    has_analytics_plan = bool(
        subscription and subscription.plan and subscription.plan.analytics_enabled
    )
    access_tier = "full" if has_analytics_plan else "free_teaser"
    upgrade_message = (
        None
        if has_analytics_plan
        else (
            "Subscribe to unlock deeper Topic Intelligence perspectives, temporal analysis, and decision context."
        )
    )

    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)

    perception_rows = (
        await db.execute(
            select(Perception.id, Perception.created_at)
            .join(User, User.id == Perception.user_id)
            .outerjoin(
                PerceptionModeration,
                PerceptionModeration.perception_id == Perception.id,
            )
            .where(
                Perception.topic_id == topic_id,
                Perception.created_at <= now,
                User.is_active.is_(True),
                (PerceptionModeration.status.is_(None))
                | PerceptionModeration.status.in_(("published", "approved")),
            )
            .order_by(Perception.created_at.asc())
        )
    ).all()
    perception_ids = [row.id for row in perception_rows]

    semantic_rows: list[tuple[CommentIntelligence, int, datetime]] = []
    participant_rows: list[tuple[CommentIntelligence, User]] = []
    if perception_ids:
        result = await db.execute(
            select(CommentIntelligence, Comment.perception_id, Comment.created_at)
            .join(Comment, Comment.id == CommentIntelligence.comment_id)
            .join(Perception, Perception.id == Comment.perception_id)
            .join(User, User.id == Comment.user_id)
            .where(
                Comment.perception_id.in_(perception_ids),
                Comment.created_at >= period_start,
                Comment.created_at <= now,
                CommentIntelligence.status == "analyzed",
                User.is_active.is_(True),
            )
            .order_by(Comment.created_at.asc())
        )
        semantic_rows = list(result.all())

        participant_result = await db.execute(
            select(CommentIntelligence, User)
            .join(Comment, Comment.id == CommentIntelligence.comment_id)
            .join(Perception, Perception.id == Comment.perception_id)
            .join(User, User.id == Comment.user_id)
            .where(
                Comment.perception_id.in_(perception_ids),
                Comment.created_at >= period_start,
                Comment.created_at <= now,
                CommentIntelligence.status == "analyzed",
                User.is_active.is_(True),
            )
        )
        participant_rows = list(participant_result.all())

    freshness = await assess_topic_freshness(db, perception_ids, period_start)
    quality = await assess_topic_quality(
        db, perception_ids, period_start, minimum=TOPIC_SAMPLE_MINIMUM
    )
    semantic_model_governance = assess_semantic_model_governance(
        [row for row, _pid, _created_at in semantic_rows],
        minimum_version_sample=TOPIC_SAMPLE_MINIMUM,
    )
    evidence_governance = assess_evidence_governance(
        analyzed_count=quality["analyzed_comment_count"],
        pending_count=quality["pending_comment_count"],
        failed_count=quality["failed_comment_count"],
        quality_status=quality["status"],
        quality_score=quality["quality_score"],
        freshness_status=freshness["status"],
        minimum=TOPIC_SAMPLE_MINIMUM,
    )

    return build_topic_intelligence(
        topic_id=topic.id,
        topic_name=topic.name,
        semantic_rows=semantic_rows,
        participant_rows=participant_rows,
        period_start=period_start,
        period_end=now,
        access_tier=access_tier,
        upgrade_available=not has_analytics_plan,
        upgrade_message=upgrade_message,
        decision_intent=decision_intent,
        minimum=TOPIC_SAMPLE_MINIMUM,
        quality_report=quality,
        freshness=freshness,
        evidence_governance=evidence_governance,
        semantic_model_governance=semantic_model_governance,
    )


@router.get("/compare", response_model=ComparativeIntelligence)
async def compare_perceptions(
    current_user: CurrentUser,
    db: DbSession,
    perception_ids: list[int] = Query(min_length=2, max_length=COMPARISON_LIMIT),
    days: int = 30,
    decision_intent: Literal[
        "research",
        "business",
        "policy",
        "journalism",
        "education",
        "product",
        "professional",
        "general_exploration",
    ] = "general_exploration",
):
    await require_analytics_access(db, current_user.id)
    if len(set(perception_ids)) != len(perception_ids):
        raise HTTPException(422, "perception_ids must be unique")
    days = max(7, min(days, 365))
    perceptions = (
        (
            await db.execute(
                select(Perception)
                .options(selectinload(Perception.topic))
                .where(
                    Perception.user_id == current_user.id,
                    Perception.id.in_(perception_ids),
                )
                .order_by(Perception.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    if len(perceptions) != len(perception_ids):
        raise HTTPException(
            404, "One or more perceptions were not found in your portfolio"
        )

    now = datetime.now(timezone.utc)
    datasets: list[dict] = []
    for perception in perceptions:
        since = max(perception.created_at, now - timedelta(days=days))
        rows = await get_comment_intelligence_rows(db, perception.id, since)
        datasets.append(
            {
                "perception_id": perception.id,
                "title": perception.body[:80],
                "topic_name": perception.topic.name if perception.topic else None,
                "rows": rows,
            }
        )
    return build_comparative_intelligence(
        datasets, minimum=MINIMUM_SAMPLE, intent=decision_intent
    )


@router.get("/profile", response_model=ProfileIntelligence)
async def profile_intelligence(
    current_user: CurrentUser,
    db: DbSession,
    days: int = PROFILE_WINDOW_DAYS,
):
    """Longitudinal intelligence across the current user's authored Perceptions."""
    await require_analytics_access(db, current_user.id)
    days = max(30, min(days, 365))
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=days)

    perceptions = (
        (
            await db.execute(
                select(Perception)
                .join(User, User.id == Perception.user_id)
                .options(selectinload(Perception.topic))
                .where(
                    Perception.user_id == current_user.id,
                    User.is_active.is_(True),
                    Perception.created_at >= period_start,
                    Perception.created_at <= now,
                )
                .order_by(Perception.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    perception_ids = [p.id for p in perceptions]
    semantic_rows = []
    if perception_ids:
        result = await db.execute(
            select(
                CommentIntelligence,
                Comment.perception_id,
                Perception.topic_id,
                Topic.name,
                Comment.created_at,
            )
            .join(Comment, Comment.id == CommentIntelligence.comment_id)
            .join(Perception, Perception.id == Comment.perception_id)
            .outerjoin(Topic, Topic.id == Perception.topic_id)
            .where(
                Comment.perception_id.in_(perception_ids),
                Comment.created_at >= period_start,
                Comment.created_at <= now,
                CommentIntelligence.status == "analyzed",
            )
            .order_by(Comment.created_at.asc())
        )
        semantic_rows = result.all()

    built = build_profile_intelligence(
        perceptions=perceptions,
        semantic_rows=semantic_rows,
        period_start=period_start,
        period_end=now,
        minimum=MINIMUM_SAMPLE,
    )
    return ProfileIntelligence(
        schema_version=built["schema_version"],
        period_start=period_start,
        period_end=now,
        period_days=days,
        sample_minimum=built["sample_minimum"],
        perception_count=built["perception_count"],
        topic_count=built["topic_count"],
        analyzed_comment_count=built["analyzed_comment_count"],
        qualifying_perception_count=built["qualifying_perception_count"],
        topics=built["topics"],
        recurring_themes=built["recurring_themes"],
        temporal=built["temporal"],
        patterns=built["patterns"],
        limitations=built["limitations"],
    )
