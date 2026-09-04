from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import sqrt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import distinct, func, select

from app.api.deps import CurrentUser, DbSession
from app.models.models import (
    AnalyticsTopic,
    Comment,
    Like,
    Perception,
    PerceptionInteraction,
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
    PerceptionAnalyticsOut,
)
from app.services.subscriptions import require_analytics_access

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
    duplicate = await db.execute(
        select(PerceptionInteraction.id).where(
            PerceptionInteraction.actor_user_id == current_user.id,
            PerceptionInteraction.perception_id == payload.perception_id,
            PerceptionInteraction.event_type == event_type,
            PerceptionInteraction.occurred_on == day,
        )
    )
    if duplicate.scalar_one_or_none() is None:
        db.add(
            PerceptionInteraction(
                actor_user_id=current_user.id,
                perception_id=payload.perception_id,
                event_type=event_type,
                occurred_on=day,
            )
        )
        await db.commit()

    return {"recorded": True, "event_type": event_type}


@router.get("/overview", response_model=AnalyticsOverviewOut)
async def analytics_overview(current_user: CurrentUser, db: DbSession, days: int = 30):
    sub = await require_analytics_access(db, current_user.id)
    days = max(7, min(days, 365))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    topic_scope = await _topic_scope(db, current_user.id, sub.plan.max_topics)
    current_filters = [Perception.created_at >= since]
    previous_filters = [
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

    filters = [Perception.created_at >= since, Perception.topic_id.is_not(None)]
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


@router.get("/perceptions/{perception_id}", response_model=PerceptionAnalyticsOut)
async def perception_analytics(
    perception_id: int, current_user: CurrentUser, db: DbSession, days: int = 30
):
    await require_analytics_access(db, current_user.id)
    days = max(7, min(days, 365))
    p = await db.scalar(
        select(Perception).where(
            Perception.id == perception_id, Perception.user_id == current_user.id
        )
    )
    if p is None:
        raise HTTPException(404, "Perception not found")
    since = max(p.created_at, datetime.now(timezone.utc) - timedelta(days=days))
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
    ids = set(
        (await db.execute(select(Like.user_id).where(Like.perception_id == p.id)))
        .scalars()
        .all()
    )
    ids.update(
        (await db.execute(select(Comment.user_id).where(Comment.perception_id == p.id)))
        .scalars()
        .all()
    )
    ids.update(
        (
            await db.execute(
                select(PerceptionInteraction.actor_user_id).where(
                    PerceptionInteraction.perception_id == p.id,
                    PerceptionInteraction.created_at >= since,
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
    geo = (
        await db.execute(
            select(User.country_code, func.count(PerceptionInteraction.id))
            .join(PerceptionInteraction, PerceptionInteraction.actor_user_id == User.id)
            .where(
                PerceptionInteraction.perception_id == p.id,
                PerceptionInteraction.created_at >= since,
            )
            .group_by(User.country_code)
            .order_by(func.count(PerceptionInteraction.id).desc())
            .limit(10)
        )
    ).all()
    return PerceptionAnalyticsOut(
        perception_id=p.id,
        period_days=days,
        created_at=p.created_at,
        topic_id=p.topic_id,
        likes=likes,
        comments=comments,
        views=views,
        shares=shares,
        unique_participants=len(ids),
        engagement_rate=round((likes + comments + shares) / views, 4) if views else 0.0,
        daily_activity=[{"date": str(d), "interactions": int(c)} for d, c in activity],
        top_countries=[
            {"country_code": c or "UNKNOWN", "interactions": int(cn)} for c, cn in geo
        ],
        methodology=[
            "Observed interaction counts for this perception; not causal inference.",
            "Likes/comments use the selected period; VIEW/SHARE are deduplicated per participant per event type per day.",
            "Engagement rate = (likes + comments + shares) / views for the selected period; 0 when no views are observed.",
            "Geography uses the interacting user's profile country when available.",
        ],
    )
