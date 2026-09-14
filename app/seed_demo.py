"""Populate a deterministic synthetic demo dataset.

This module is for development, QA, analytics validation, and frontend
testing only.

It must never be required for normal application startup or production
reference-data initialization.

The seed removes only users whose email matches the dedicated demo-user
patterns, then recreates the synthetic dataset from scratch.

Usage:
    docker compose exec api env ALLOW_DEMO_SEED=true python -m app.seed_demo
"""

import asyncio
import os
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.models import (
    AnalyticsTopic,
    Comment,
    CommentIntelligence,
    Follow,
    Like,
    Perception,
    PerceptionInteraction,
    Plan,
    Subscription,
    Topic,
    TopicFollow,
    User,
    VerificationApplication,
)
from app.seed_data.demo import (
    COMMENT_BODIES,
    COUNTRIES,
    DEMO_PASSWORD,
    DEMO_ROLE_CODES,
    FIXTURE_BODIES,
    PRIMARY_TOPICS,
    PROFILES,
    SEED,
    SEMANTIC_THEMES,
    SUBSCRIPTION_CODES,
    TOPIC_FOCUS,
    TOPIC_WEIGHTS,
)
from app.services.professional_taxonomy import ROLE_MAP


def require_demo_seed_permission() -> None:
    """Prevent accidental execution of the synthetic demo seed."""

    allowed = os.getenv("ALLOW_DEMO_SEED", "").strip().lower()

    if allowed != "true":
        raise RuntimeError(
            "Demo seeding is disabled. "
            "Run it explicitly with "
            "ALLOW_DEMO_SEED=true in a non-production environment."
        )


def weighted_topic_names() -> list[str]:
    """Return topic names expanded according to their configured weights."""

    names: list[str] = []

    for topic_name, weight in TOPIC_WEIGHTS.items():
        names.extend([topic_name] * weight)

    return names


def perception_body(
    topic_name: str,
    index: int,
    current_period: bool,
) -> str:
    """Build deterministic synthetic perception text."""

    focus = TOPIC_FOCUS[topic_name]

    if current_period:
        variants = [
            (
                f"Current-period signal {index}: "
                f"people are increasingly discussing {focus}."
            ),
            (
                f"Recent perception {index}: "
                f"my experience suggests that {focus} is changing quickly."
            ),
            (
                f"Signal {index}: "
                f"there is growing interest in how {focus} affects "
                f"everyday decisions."
            ),
            (
                f"Current observation {index}: "
                f"the strongest discussion I see around "
                f"{topic_name.lower()} is connected to {focus}."
            ),
            (
                f"Recent view {index}: "
                f"better evidence about {focus} could improve "
                f"decision-making."
            ),
        ]
    else:
        variants = [
            (
                f"Previous-period signal {index}: "
                f"people were already discussing {focus}."
            ),
            (
                f"Earlier perception {index}: "
                f"my experience showed that {focus} mattered significantly."
            ),
            (
                f"Historical signal {index}: "
                f"there was noticeable interest in how {focus} affected "
                f"everyday decisions."
            ),
            (
                f"Previous observation {index}: "
                f"the discussion around {topic_name.lower()} included "
                f"questions about {focus}."
            ),
            (
                f"Earlier view {index}: "
                f"more evidence about {focus} would have helped "
                f"decision-making."
            ),
        ]

    return variants[index % len(variants)]


async def seed_demo() -> None:
    """Recreate the complete deterministic synthetic demo dataset."""

    require_demo_seed_permission()

    random.seed(SEED)

    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # ------------------------------------------------------------------
        # 1. Remove only the dedicated demo users.
        #
        # Related rows are removed through the configured database
        # foreign-key cascades and ORM relationships.
        # ------------------------------------------------------------------
        demo_users_result = await db.execute(
            select(User).where(
                User.email.like("demo%@perception.local")
                | User.email.like("demo%@example.com")
            )
        )

        demo_users = demo_users_result.scalars().all()

        for user in demo_users:
            await db.delete(user)

        await db.commit()

        # ------------------------------------------------------------------
        # 2. Load and validate reference data.
        # ------------------------------------------------------------------
        topic_result = await db.execute(select(Topic))
        topic_rows = topic_result.scalars().all()

        if not topic_rows:
            raise RuntimeError(
                "No topics exist. Run `python -m app.seed` before "
                "running the demo seed."
            )

        topics = {topic.name: topic for topic in topic_rows}

        missing_topics = [name for name in TOPIC_WEIGHTS if name not in topics]

        if missing_topics:
            raise RuntimeError(
                "Required reference topics are missing: " + ", ".join(missing_topics)
            )

        plan_result = await db.execute(select(Plan))
        plan_rows = plan_result.scalars().all()

        plans = {plan.code: plan for plan in plan_rows}

        required_plans = {
            "free",
            "professional",
            "research",
            "business",
        }

        missing_plans = sorted(required_plans - plans.keys())

        if missing_plans:
            raise RuntimeError(
                "Required reference plans are missing: " + ", ".join(missing_plans)
            )

        # ------------------------------------------------------------------
        # 3. Create deterministic demo users.
        #
        # User.role is the application/RBAC role.
        #
        # Professional taxonomy codes belong in:
        #   - professional_roles
        #   - primary_professional_role
        #   - verified_professional_roles
        #
        # Verification is represented by:
        #   - verification_status
        #   - verification_badge
        # ------------------------------------------------------------------
        password_hash = hash_password(DEMO_PASSWORD)

        users: list[User] = []

        for index, (
            name,
            profession,
            analytics_focus,
        ) in enumerate(PROFILES):
            role_code = DEMO_ROLE_CODES[index]

            role_definition = ROLE_MAP.get(role_code)

            if role_definition is None:
                raise RuntimeError(
                    f"Demo professional role '{role_code}' is missing " "from ROLE_MAP."
                )

            country_code, country_name, city = COUNTRIES[index % len(COUNTRIES)]

            primary_topic_name = PRIMARY_TOPICS[index % len(PRIMARY_TOPICS)]

            primary_topic = topics[primary_topic_name]

            verified_demo_user = index < 12

            user = User(
                name=name,
                role="USER",
                email=f"demo{index + 1:02d}@example.com",
                password_hash=password_hash,
                profession=profession,
                professional_focus=analytics_focus,
                country_code=country_code,
                region=country_name,
                city=city,
                analytics_specialties=[
                    primary_topic.id,
                ],
                professional_industries=[],
                professional_roles=[
                    role_code,
                ],
                primary_professional_role=role_code,
                verified_professional_roles=([role_code] if verified_demo_user else []),
                primary_analytics_topic_id=primary_topic.id,
                verification_status=(
                    "APPROVED" if verified_demo_user else "NOT_APPLIED"
                ),
                verification_badge=("PROFESSIONAL" if verified_demo_user else None),
                bio=(
                    f"Demo profile for {profession.lower()} working on "
                    f"{analytics_focus.lower()}."
                ),
                is_active=True,
            )

            users.append(user)
            db.add(user)

        await db.flush()

        # ------------------------------------------------------------------
        # 4. Create deterministic subscriptions for the first ten users.
        # ------------------------------------------------------------------
        subscriptions: list[Subscription] = []

        for index, plan_code in enumerate(SUBSCRIPTION_CODES):
            user = users[index]
            plan = plans[plan_code]

            if plan_code == "free":
                continue

            subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status="ACTIVE",
                provider="demo_seed",
                starts_at=now - timedelta(days=45),
                current_period_start=now - timedelta(days=45),
                current_period_end=now + timedelta(days=45),
                cancel_at_period_end=False,
            )

            subscriptions.append(subscription)
            db.add(subscription)

        await db.flush()

        # ------------------------------------------------------------------
        # 5. Add analytics-topic access for non-free demo users.
        # ------------------------------------------------------------------
        analytics_topics: list[AnalyticsTopic] = []

        for index, plan_code in enumerate(SUBSCRIPTION_CODES):
            if plan_code == "free":
                continue

            user = users[index]
            plan = plans[plan_code]

            primary_name = PRIMARY_TOPICS[index % len(PRIMARY_TOPICS)]

            selected_names = list(
                dict.fromkeys(
                    [primary_name]
                    + [
                        "Business",
                        "Technology",
                        "Education",
                        "Health",
                        "Economy",
                    ]
                )
            )

            selected_names = selected_names[: plan.max_topics]

            for topic_name in selected_names:
                analytics_topic = AnalyticsTopic(
                    user_id=user.id,
                    topic_id=topics[topic_name].id,
                )

                analytics_topics.append(analytics_topic)
                db.add(analytics_topic)

        await db.flush()

        # ------------------------------------------------------------------
        # 6. Create approved verification applications for verified
        #    analytics users.
        # ------------------------------------------------------------------
        verification_applications: list[VerificationApplication] = []

        for index, user in enumerate(users[:12]):
            if index >= len(SUBSCRIPTION_CODES):
                continue

            plan_code = SUBSCRIPTION_CODES[index]

            if plan_code == "free":
                continue

            role_code = DEMO_ROLE_CODES[index]
            primary_topic_name = PRIMARY_TOPICS[index % len(PRIMARY_TOPICS)]

            application = VerificationApplication(
                user_id=user.id,
                profession=user.profession or "Professional",
                focus=user.professional_focus or "Professional research",
                industry_codes=[],
                professional_role_codes=[role_code],
                primary_professional_role=role_code,
                primary_topic_id=topics[primary_topic_name].id,
                requested_topic_ids=[
                    topics[primary_topic_name].id,
                ],
                evidence=(
                    "Synthetic demo evidence for analytics verification. "
                    "This record exists only for development and QA."
                ),
                status="APPROVED",
                badge="PROFESSIONAL",
                reviewer_note=("Automatically approved synthetic demo verification."),
            )

            verification_applications.append(application)
            db.add(application)

        await db.flush()

        # ------------------------------------------------------------------
        # 7. Add subscription edge cases for analytics validation.
        # ------------------------------------------------------------------
        expired_subscription = Subscription(
            user_id=users[10].id,
            plan_id=plans["professional"].id,
            status="EXPIRED",
            provider="demo_seed",
            starts_at=now - timedelta(days=45),
            current_period_start=now - timedelta(days=45),
            current_period_end=now - timedelta(days=1),
            cancel_at_period_end=False,
        )

        past_due_current = Subscription(
            user_id=users[11].id,
            plan_id=plans["professional"].id,
            status="PAST_DUE",
            provider="demo_seed",
            starts_at=now - timedelta(days=45),
            current_period_start=now - timedelta(days=45),
            current_period_end=now + timedelta(days=10),
            cancel_at_period_end=False,
        )

        past_due_expired = Subscription(
            user_id=users[12].id,
            plan_id=plans["professional"].id,
            status="PAST_DUE",
            provider="demo_seed",
            starts_at=now - timedelta(days=45),
            current_period_start=now - timedelta(days=45),
            current_period_end=now - timedelta(days=1),
            cancel_at_period_end=False,
        )

        db.add_all(
            [
                expired_subscription,
                past_due_current,
                past_due_expired,
            ]
        )

        # ------------------------------------------------------------------
        # 8. Topic follows.
        # ------------------------------------------------------------------
        topic_follow_pairs: set[tuple[int, int]] = set()

        for user in users:
            available_topics = list(topics.values())

            followed_topics = random.sample(
                available_topics,
                k=min(4, len(available_topics)),
            )

            for topic in followed_topics:
                pair = (user.id, topic.id)

                if pair in topic_follow_pairs:
                    continue

                topic_follow_pairs.add(pair)

                db.add(
                    TopicFollow(
                        user_id=user.id,
                        topic_id=topic.id,
                    )
                )

        # ------------------------------------------------------------------
        # 9. User follows.
        # ------------------------------------------------------------------
        user_follow_pairs: set[tuple[int, int]] = set()

        for user in users:
            candidates = [candidate for candidate in users if candidate.id != user.id]

            followed_users = random.sample(
                candidates,
                k=min(5, len(candidates)),
            )

            for followed_user in followed_users:
                pair = (user.id, followed_user.id)

                if pair in user_follow_pairs:
                    continue

                user_follow_pairs.add(pair)

                db.add(
                    Follow(
                        follower_id=user.id,
                        followed_id=followed_user.id,
                    )
                )

        await db.flush()

        # ------------------------------------------------------------------
        # 10. Create normal perceptions.
        #
        #     70 previous-period perceptions:
        #         30–59 days old
        #
        #     250 current-period perceptions:
        #         0–29 days old
        # ------------------------------------------------------------------
        topic_pool = weighted_topic_names()

        perceptions: list[Perception] = []

        for index in range(320):
            current_period = index >= 70

            if current_period:
                age_days = random.randint(0, 29)
            else:
                age_days = random.randint(30, 59)

            created_at = now - timedelta(
                days=age_days,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            topic_name = topic_pool[index % len(topic_pool)]
            topic = topics[topic_name]

            author = users[index % len(users)]

            perception = Perception(
                user_id=author.id,
                topic_id=topic.id,
                body=perception_body(
                    topic_name=topic_name,
                    index=index,
                    current_period=current_period,
                ),
                created_at=created_at,
            )

            perceptions.append(perception)
            db.add(perception)

        await db.flush()

        # ------------------------------------------------------------------
        # 11. Add deterministic likes and comments to normal perceptions.
        # ------------------------------------------------------------------
        normal_comments: list[Comment] = []

        high_engagement_topics = {
            "Business",
            "Technology",
            "Education",
        }

        medium_engagement_topics = {
            "Health",
            "Economy",
            "Science",
        }

        topic_names_by_id = {topic.id: topic.name for topic in topics.values()}

        for index, perception in enumerate(perceptions):
            topic_name = topic_names_by_id.get(perception.topic_id)

            if topic_name in high_engagement_topics:
                like_count = random.randint(6, 13)
                comment_count = random.randint(2, 5)
            elif topic_name in medium_engagement_topics:
                like_count = random.randint(4, 10)
                comment_count = random.randint(1, 4)
            else:
                like_count = random.randint(2, 7)
                comment_count = random.randint(0, 3)

            like_candidates = [user for user in users if user.id != perception.user_id]

            like_users = random.sample(
                like_candidates,
                k=min(like_count, len(like_candidates)),
            )

            for like_user in like_users:
                db.add(
                    Like(
                        user_id=like_user.id,
                        perception_id=perception.id,
                    )
                )

            comment_candidates = [
                user for user in users if user.id != perception.user_id
            ]

            comment_users = random.sample(
                comment_candidates,
                k=min(comment_count, len(comment_candidates)),
            )

            for comment_position, comment_user in enumerate(comment_users):
                comment = Comment(
                    user_id=comment_user.id,
                    perception_id=perception.id,
                    body=COMMENT_BODIES[
                        (index + comment_position) % len(COMMENT_BODIES)
                    ],
                    created_at=perception.created_at
                    + timedelta(
                        hours=1 + comment_position,
                    ),
                )

                normal_comments.append(comment)
                db.add(comment)

        await db.flush()

        # ------------------------------------------------------------------
        # 12. Scenario fixtures for the first demo user.
        #
        #     These deliberately exercise:
        #       - zero-comment state
        #       - recent conversation
        #       - mid-period conversation
        #       - older conversation
        #       - four-comment threshold
        # ------------------------------------------------------------------
        scenario_specs = [
            (
                "Business",
                5,
                "Zero-comment fixture",
            ),
            (
                "Technology",
                10,
                "Recent conversation fixture",
            ),
            (
                "Business",
                45,
                "Mid-period conversation fixture",
            ),
            (
                "Education",
                80,
                "Older conversation fixture",
            ),
            (
                "Economy",
                40,
                "Four-comment threshold fixture",
            ),
        ]

        scenario_perceptions: list[Perception] = []

        for topic_name, age_days, body in scenario_specs:
            perception = Perception(
                user_id=users[0].id,
                topic_id=topics[topic_name].id,
                body=body,
                created_at=now
                - timedelta(
                    days=age_days,
                    hours=3,
                ),
            )

            scenario_perceptions.append(perception)
            db.add(perception)

        await db.flush()

        zero_comment_fixture = scenario_perceptions[0]
        recent_conversation_fixture = scenario_perceptions[1]
        mid_conversation_fixture = scenario_perceptions[2]
        old_conversation_fixture = scenario_perceptions[3]
        threshold_fixture = scenario_perceptions[4]

        # ------------------------------------------------------------------
        # 13. Zero-comment fixture.
        #
        #     Nine actors each:
        #       - Like the perception
        #       - Create a VIEW interaction
        #
        #     No comments are created.
        # ------------------------------------------------------------------
        zero_comment_actors = users[1:10]

        for actor in zero_comment_actors:
            db.add(
                Like(
                    user_id=actor.id,
                    perception_id=zero_comment_fixture.id,
                )
            )

            occurred_on = zero_comment_fixture.created_at + timedelta(hours=2)

            db.add(
                PerceptionInteraction(
                    actor_user_id=actor.id,
                    perception_id=zero_comment_fixture.id,
                    event_type="VIEW",
                    occurred_on=occurred_on,
                )
            )

        # ------------------------------------------------------------------
        # 14. Rich conversation fixtures.
        #
        #     Six parent comments plus two replies for each:
        #       - recent Technology
        #       - mid-period Business
        #       - old Education
        # ------------------------------------------------------------------
        rich_fixtures = [
            recent_conversation_fixture,
            mid_conversation_fixture,
            old_conversation_fixture,
        ]

        rich_actor_sets = [
            users[1:7],
            users[7:13],
            users[13:19],
        ]

        fixture_comments: list[Comment] = []

        for fixture_index, (
            fixture,
            actor_set,
        ) in enumerate(
            zip(
                rich_fixtures,
                rich_actor_sets,
                strict=True,
            )
        ):
            parent_comments: list[Comment] = []

            for comment_position, actor in enumerate(actor_set):
                comment = Comment(
                    user_id=actor.id,
                    perception_id=fixture.id,
                    body=FIXTURE_BODIES[
                        (fixture_index * 6 + comment_position) % len(FIXTURE_BODIES)
                    ],
                    created_at=fixture.created_at
                    + timedelta(
                        hours=1 + comment_position,
                    ),
                )

                parent_comments.append(comment)
                fixture_comments.append(comment)
                db.add(comment)

            await db.flush()

            reply_actors = [
                users[19],
                users[20],
            ]

            for reply_position, parent_comment in enumerate(parent_comments[:2]):
                reply = Comment(
                    user_id=reply_actors[reply_position].id,
                    perception_id=fixture.id,
                    parent_comment_id=parent_comment.id,
                    body=FIXTURE_BODIES[
                        (fixture_index * 2 + reply_position + 2) % len(FIXTURE_BODIES)
                    ],
                    created_at=parent_comment.created_at + timedelta(hours=2),
                )

                fixture_comments.append(reply)
                db.add(reply)

        # ------------------------------------------------------------------
        # 15. Four-comment threshold fixture.
        # ------------------------------------------------------------------
        threshold_actors = users[20:24]

        for comment_position, actor in enumerate(threshold_actors):
            comment = Comment(
                user_id=actor.id,
                perception_id=threshold_fixture.id,
                body=FIXTURE_BODIES[comment_position % len(FIXTURE_BODIES)],
                created_at=threshold_fixture.created_at
                + timedelta(
                    hours=1 + comment_position,
                ),
            )

            fixture_comments.append(comment)
            db.add(comment)

        await db.flush()

        # ------------------------------------------------------------------
        # 16. Comment intelligence.
        #
        #     Applies to both normal comments and scenario comments.
        # ------------------------------------------------------------------
        all_comments = [
            *normal_comments,
            *fixture_comments,
        ]

        sentiments = [
            "positive",
            "neutral",
            "mixed",
            "negative",
        ]

        stances = [
            "supportive",
            "challenging",
            "mixed",
            "unclear",
        ]

        for index, comment in enumerate(all_comments):
            db.add(
                CommentIntelligence(
                    comment_id=comment.id,
                    status="analyzed",
                    sentiment=sentiments[index % len(sentiments)],
                    stance=stances[index % len(stances)],
                    themes=[SEMANTIC_THEMES[index % len(SEMANTIC_THEMES)]],
                    is_question=index % 5 == 0,
                    has_concern=index % 4 == 3,
                    agreement_signal=index % 4 == 0,
                    disagreement_signal=index % 4 == 1,
                    quality_score=0.9,
                    model_version="demo-seed-v1",
                    analyzed_at=comment.created_at,
                )
            )

        # ------------------------------------------------------------------
        # 17. VIEW / SHARE interaction events for normal perceptions.
        #
        #     Previous period:
        #         1–3 events
        #
        #     Current period:
        #         3–10 events
        #
        #     random.sample() is used instead of random.choices() so that
        #     the same actor cannot generate duplicate events for the same
        #     perception on the same day.
        # ------------------------------------------------------------------
        for index, perception in enumerate(perceptions):
            is_current_period = index >= 70

            event_count = (
                random.randint(3, 10) if is_current_period else random.randint(1, 3)
            )

            actor_candidates = [user for user in users if user.id != perception.user_id]

            event_count = min(
                event_count,
                len(actor_candidates),
            )

            actors = random.sample(
                actor_candidates,
                k=event_count,
            )

            for position, actor in enumerate(actors):
                event_time = perception.created_at + timedelta(
                    hours=random.randint(1, 48),
                )

                if event_time >= now:
                    event_time = now - timedelta(
                        minutes=1 + position,
                    )

                interaction_type = "SHARE" if (index + position) % 5 == 0 else "VIEW"

                db.add(
                    PerceptionInteraction(
                        actor_user_id=actor.id,
                        perception_id=perception.id,
                        event_type=interaction_type,
                        occurred_on=event_time,
                    )
                )

        # ------------------------------------------------------------------
        # 18. Commit the complete deterministic dataset.
        # ------------------------------------------------------------------
        await db.commit()

    # ----------------------------------------------------------------------
    # Completion summary.
    # ----------------------------------------------------------------------
    print("Demo seed complete.")
    print(f"  Users: {len(users)}")
    print("  Perceptions: " f"{len(perceptions) + len(scenario_perceptions)}")
    print(
        "  Analytics accounts: "
        f"{sum(1 for code in SUBSCRIPTION_CODES if code != 'free')}"
    )
    print("  Scenario fixtures: " f"{len(scenario_perceptions)}")
    print("  Subscription fixtures: expired + past_due")
    print("")
    print("Frontend test accounts:")
    print(f"  Password: {DEMO_PASSWORD}")
    print("  demo01@example.com")
    print("  demo02@example.com")
    print("  demo03@example.com")
    print("  ...")
    print("  demo30@example.com")


if __name__ == "__main__":
    asyncio.run(seed_demo())
