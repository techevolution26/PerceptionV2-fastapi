"""Populate a realistic demo dataset for frontend + analytics testing.

Usage:
    docker compose exec api python -m app.seed_demo

The seed is deterministic and safe to re-run for the demo accounts: existing
users whose email starts with ``demo`` and uses either ``@perception.local``
or ``@example.com`` are removed and recreated. Production/reference data is left untouched.

Demo password for every account: Demo1234!
"""

import asyncio
from datetime import datetime, timedelta, timezone
import random

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.services.professional_taxonomy import ROLE_MAP
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

SEED = 20260903
DEMO_PASSWORD = "Demo1234!"

COUNTRIES = [
    ("KE", "Kenya", "Nairobi"),
    ("KE", "Kenya", "Mombasa"),
    ("KE", "Kenya", "Kilifi"),
    ("UG", "Uganda", "Kampala"),
    ("TZ", "Tanzania", "Dar es Salaam"),
    ("NG", "Nigeria", "Lagos"),
    ("GH", "Ghana", "Accra"),
    ("ZA", "South Africa", "Johannesburg"),
    ("GB", "United Kingdom", "London"),
    ("US", "United States", "New York"),
]

# A deliberate concentration around five topics makes the analytics dashboard
# interesting for the Professional demo account while still leaving a long tail.
TOPIC_WEIGHTS = {
    "Business": 18,
    "Technology": 17,
    "Education": 14,
    "Health": 10,
    "Economy": 8,
    "Science": 7,
    "Culture": 6,
    "Society": 5,
    "Lifestyle": 4,
    "Sports": 3,
    "Religion": 2,
    "Politics": 1,
}

PROFILES = [
    ("Amina Hassan", "Product Manager", "Digital products and customer research"),
    ("Brian Otieno", "Software Engineer", "Applied technology and AI adoption"),
    ("Grace Wanjiku", "Teacher", "Learning outcomes and education access"),
    ("Daniel Mwangi", "Business Analyst", "SME growth and market intelligence"),
    ("Faith Njeri", "Public Health Specialist", "Community health and prevention"),
    ("Kevin Ouma", "Researcher", "Data, evidence and social research"),
    ("Mercy Achieng", "Economist", "Household economics and consumer behaviour"),
    ("Samuel Kibet", "Entrepreneur", "Retail, logistics and local markets"),
    ("Esther Wambui", "UX Designer", "Human behaviour and digital experiences"),
    ("Joseph Kamau", "Data Analyst", "Decision intelligence and analytics"),
    ("Lilian Atieno", "Journalist", "Society, media and public opinion"),
    ("Peter Kariuki", "Agribusiness Consultant", "Food systems and rural markets"),
    ("Ruth Muthoni", "Nurse", "Health education and patient experience"),
    ("Mark Kiptoo", "Developer", "Developer tools and technology adoption"),
    ("Irene Chebet", "Lecturer", "Higher education and workforce readiness"),
    ("Alex Maina", "Founder", "Startups, product-market fit and innovation"),
    ("Susan Adhiambo", "Community Organizer", "Community development and inclusion"),
    ("Victor Omondi", "Financial Advisor", "Personal finance and economic resilience"),
    ("Naomi Jepchirchir", "Scientist", "Science communication and public trust"),
    ("John Mutua", "Sports Coach", "Youth sport and performance"),
    (
        "Caroline Wairimu",
        "Marketing Strategist",
        "Brand perception and consumer behaviour",
    ),
    ("Eric Odhiambo", "Cybersecurity Analyst", "Digital trust and online safety"),
    ("Miriam Kilonzo", "Policy Researcher", "Public policy and social outcomes"),
    (
        "Collins Barasa",
        "Operations Manager",
        "Supply chains and operational efficiency",
    ),
    ("Diana Akinyi", "Psychologist", "Wellbeing, behaviour and community support"),
    ("Felix Njoroge", "Architect", "Cities, housing and sustainable development"),
    ("Beatrice Nyambura", "HR Specialist", "Workplace culture and future skills"),
    ("George Were", "Teacher", "Digital learning and classroom innovation"),
    ("Ann Waithera", "Consultant", "Organisational strategy and transformation"),
    ("David Kiplangat", "Farmer", "Agriculture, climate and local economies"),
]

TOPIC_FOCUS = {
    "Business": "how businesses understand customers, markets and growth",
    "Technology": "how people adopt technology and how it changes everyday work",
    "Education": "how learning systems affect skills, opportunity and outcomes",
    "Health": "how communities understand health, prevention and wellbeing",
    "Economy": "how economic conditions affect households, prices and decisions",
    "Science": "how people understand scientific evidence and discovery",
    "Culture": "how culture shapes behaviour, identity and community life",
    "Society": "how social changes affect communities and relationships",
    "Lifestyle": "how people balance work, wellbeing and everyday choices",
    "Sports": "how sport affects youth, health and community identity",
    "Religion": "how faith and spirituality shape community life",
    "Politics": "how people perceive public policy and political change",
}


# Fix the one intentionally simple country list typo without making the seed
# dependent on a second data structure.
COUNTRIES[8] = ("GB", "United Kingdom", "London")


def weighted_topic_names() -> list[str]:
    names: list[str] = []
    for name, weight in TOPIC_WEIGHTS.items():
        names.extend([name] * weight)
    return names


def perception_body(topic: str, index: int, current: bool) -> str:
    phase = (
        "Recent community discussions" if current else "Earlier community discussions"
    )
    focus = TOPIC_FOCUS[topic]
    variants = [
        f"{phase} suggest that {focus}. What are people actually experiencing on the ground?",
        f"My observation is that {focus}. I would like to compare this perspective with others.",
        f"A recurring question is whether {focus}. Different communities may be seeing very different outcomes.",
        f"From conversations in my work, I keep noticing that {focus}. The pattern deserves closer attention.",
        f"There seems to be a growing perception that {focus}. More voices could help us understand why.",
    ]
    return variants[index % len(variants)]


async def seed_demo() -> None:
    random.seed(SEED)
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Remove only this script's demo accounts. Cascades remove their
        # perceptions, likes, comments, follows, subscriptions and analytics rows.
        demo_users = (
            (
                await db.execute(
                    select(User.id).where(
                        User.email.like("demo%@perception.local")
                        | User.email.like("demo%@example.com")
                    )
                )
            )
            .scalars()
            .all()
        )
        if demo_users:
            await db.execute(delete(User).where(User.id.in_(demo_users)))
            await db.commit()

        topics = {
            topic.name: topic
            for topic in (await db.execute(select(Topic))).scalars().all()
        }
        if not topics:
            raise RuntimeError("No topics found. Run `python -m app.seed` first.")

        plans = {
            plan.code: plan for plan in (await db.execute(select(Plan))).scalars().all()
        }
        for required in ("free", "professional", "research", "business"):
            if required not in plans:
                raise RuntimeError(
                    f"Missing plan `{required}`. Run `python -m app.seed` first."
                )

        # ------------------------------------------------------------------
        # Users
        # ------------------------------------------------------------------
        users: list[User] = []
        # Structured demo identities keep the seeded dataset aligned with the
        # professional taxonomy used by the verification and profile UI.
        demo_role_codes = [
            "product_manager", "software_engineer", "teacher", "business_analyst",
            "public_health_specialist", "research_scientist", "economist", "entrepreneur",
            "ux_designer", "data_scientist", "journalist", "agricultural_economist",
            "nurse", "web_developer", "lecturer", "founder", "social_worker",
            "financial_advisor", "research_scientist", "coach", "management_consultant",
            "cybersecurity_specialist", "policy_analyst", "operations_manager", "psychologist",
            "architect", "human_resources_specialist", "teacher", "management_consultant", "farmer",
        ]
        primary_topics = [
            "Business",
            "Technology",
            "Education",
            "Health",
            "Economy",
            "Science",
            "Culture",
            "Society",
            "Lifestyle",
            "Sports",
        ]

        for index, (name, profession, focus) in enumerate(PROFILES, start=1):
            country_code, region, city = COUNTRIES[(index - 1) % len(COUNTRIES)]
            primary_name = primary_topics[(index - 1) % len(primary_topics)]
            primary_topic = topics.get(primary_name)
            specialty_names = [primary_name]
            for extra in ("Business", "Technology", "Education", "Health", "Economy"):
                if (
                    extra != primary_name
                    and len(specialty_names) < 3
                    and extra in topics
                ):
                    specialty_names.append(extra)
            # User.analytics_specialties stores AnalyticsTopic IDs, not topic names.

            specialties = [topics[name].id for name in specialty_names]

            role_code = demo_role_codes[index - 1]
            role_definition = ROLE_MAP[role_code]
            verified = index <= 12
            user = User(
                name=name,
                role="USER",
                email=f"demo{index:02d}@example.com",
                password_hash=hash_password(DEMO_PASSWORD),
                profession=profession,
                professional_focus=focus,
                professional_industries=[role_definition["industry_code"]],
                professional_roles=[role_code],
                primary_professional_role=role_code,
                verified_professional_roles=[role_code] if verified else [],
                country_code=country_code,
                region=region,
                city=city,
                analytics_specialties=specialties,
                primary_analytics_topic_id=primary_topic.id if primary_topic else None,
                verification_status="VERIFIED" if verified else "NOT_APPLIED",
                verification_badge="PROFESSIONAL" if verified else None,
                bio=f"Demo participant interested in {focus.lower()}.",
            )
            users.append(user)
            db.add(user)

        await db.flush()

        # Give the first few users analytics access. These are the accounts to
        # use when testing the analytics frontend.
        subscription_codes = [
            "professional",
            "professional",
            "professional",
            "research",
            "business",
            "professional",
            "research",
            "professional",
            "free",
            "free",
        ]
        analytics_users: list[User] = []
        for index, user in enumerate(users):
            code = (
                subscription_codes[index] if index < len(subscription_codes) else "free"
            )
            plan = plans[code]
            if code != "free":
                analytics_users.append(user)
                start = now - timedelta(days=45)
                db.add(
                    Subscription(
                        user_id=user.id,
                        plan_id=plan.id,
                        status="ACTIVE",
                        provider="demo_seed",
                        starts_at=start,
                        current_period_start=start,
                        current_period_end=now + timedelta(days=45),
                        cancel_at_period_end=False,
                    )
                )

                selected_names = list(
                    dict.fromkeys(
                        [
                            user.profession
                            and primary_topics[index % len(primary_topics)]
                        ]
                        + ["Business", "Technology", "Education", "Health", "Economy"]
                    )
                )
                selected_names = [name for name in selected_names if name in topics][
                    : plan.max_topics
                ]
                for topic_name in selected_names:
                    db.add(
                        AnalyticsTopic(user_id=user.id, topic_id=topics[topic_name].id)
                    )

                if user.verification_status == "VERIFIED":
                    db.add(
                        VerificationApplication(
                            user_id=user.id,
                            profession=user.profession or "Professional",
                            industry_codes=list(user.professional_industries or []),
                            professional_role_codes=list(user.professional_roles or []),
                            primary_professional_role=user.primary_professional_role,
                            focus=user.professional_focus or "General research",
                            primary_topic_id=None,
                            requested_topic_ids=[],
                            evidence="Synthetic demo evidence for frontend testing.",
                            status="APPROVED",
                            badge="PROFESSIONAL",
                            reviewer_note="Demo seed record.",
                        )
                    )

        # Subscription edge cases used by the release/entitlement tests.
        # demo11 is expired; demo12 is past_due but still inside its paid period;
        # demo13 is past_due with an expired period and must fail closed.
        for user_index, code, status, period_end_offset in [
            (11, "professional", "EXPIRED", -1),
            (12, "professional", "past_due", 10),
            (13, "professional", "past_due", -1),
        ]:
            user = users[user_index - 1]
            plan = plans[code]
            start = now - timedelta(days=45)
            db.add(
                Subscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    status=status,
                    provider="demo_seed",
                    starts_at=start,
                    current_period_start=start,
                    current_period_end=now + timedelta(days=period_end_offset),
                    cancel_at_period_end=False,
                )
            )

        # ------------------------------------------------------------------
        # Topic follows + user follows
        # ------------------------------------------------------------------
        for user in users:
            follow_topics = random.sample(list(topics.values()), k=min(4, len(topics)))
            for topic in follow_topics:
                db.add(TopicFollow(user_id=user.id, topic_id=topic.id))

        for user in users:
            candidates = [candidate for candidate in users if candidate.id != user.id]
            for followed in random.sample(candidates, k=5):
                db.add(Follow(follower_id=user.id, followed_id=followed.id))

        await db.flush()

        # ------------------------------------------------------------------
        # Perceptions: 70 previous-period + 250 current-period records.
        # The current period is intentionally busier so growth/momentum and
        # opportunity cards have something meaningful to show.
        # ------------------------------------------------------------------
        weighted_topics = weighted_topic_names()
        perceptions: list[Perception] = []

        for index in range(320):
            current = index >= 70
            if current:
                age_days = random.randint(0, 29)
            else:
                age_days = random.randint(30, 59)

            created_at = now - timedelta(
                days=age_days,
                hours=random.randint(0, 20),
                minutes=random.randint(0, 59),
            )
            topic_name = weighted_topics[
                (index * 17 + random.randint(0, 11)) % len(weighted_topics)
            ]
            topic = topics[topic_name]
            author = users[(index * 7 + index // 13) % len(users)]
            body = perception_body(topic_name, index, current)

            perception = Perception(
                user_id=author.id,
                topic_id=topic.id,
                body=body,
                created_at=created_at,
                updated_at=created_at,
            )
            perceptions.append(perception)
            db.add(perception)

        await db.flush()

        # ------------------------------------------------------------------
        # Likes + comments. Interaction counts vary by topic to create visible
        # differences in signal strength and opportunity ranking.
        # ------------------------------------------------------------------
        for index, perception in enumerate(perceptions):
            topic_name = next(
                name
                for name, topic in topics.items()
                if topic.id == perception.topic_id
            )
            if topic_name in {"Business", "Technology", "Education"}:
                like_count = random.randint(6, 13)
                comment_count = random.randint(2, 5)
            elif topic_name in {"Health", "Economy", "Science"}:
                like_count = random.randint(4, 10)
                comment_count = random.randint(1, 4)
            else:
                like_count = random.randint(2, 7)
                comment_count = random.randint(0, 3)

            likers = random.sample(users, k=min(like_count, len(users)))
            for position, liker in enumerate(likers):
                like_time = perception.created_at + timedelta(
                    hours=random.randint(1, 72), minutes=random.randint(0, 59)
                )
                if like_time > now:
                    like_time = now - timedelta(minutes=position + 1)
                db.add(
                    Like(
                        user_id=liker.id,
                        perception_id=perception.id,
                        created_at=like_time,
                        updated_at=like_time,
                    )
                )

            commenters = (
                random.sample(users, k=min(max(1, comment_count), len(users)))
                if comment_count
                else []
            )
            for position, commenter in enumerate(commenters[:comment_count]):
                comment_time = perception.created_at + timedelta(
                    hours=random.randint(1, 96), minutes=random.randint(0, 59)
                )
                if comment_time > now:
                    comment_time = now - timedelta(minutes=position + 1)
                db.add(
                    Comment(
                        user_id=commenter.id,
                        perception_id=perception.id,
                        body=[
                            "Interesting perspective — I have seen something similar.",
                            "This is useful. I would like to see how it varies by location.",
                            "I agree, although my experience has been slightly different.",
                            "What evidence would help us test this perception further?",
                            "This could be a useful signal for decision-making.",
                        ][(index + position) % 5],
                        created_at=comment_time,
                        updated_at=comment_time,
                    )
                )

        await db.flush()

        # ------------------------------------------------------------------
        # Deterministic analytics fixtures. These deliberately exercise the
        # boundaries the product contract depends on: a perception can have
        # engagement without a conversation, while comment-derived audience
        # and semantic intelligence only appear when comments exist. The first
        # user receives a longitudinal portfolio spanning three 30-day buckets.
        # ------------------------------------------------------------------
        demo_owner = users[0]
        scenario_specs = [
            ("Business", 5, "Zero-comment fixture"),
            ("Technology", 10, "Recent conversation fixture"),
            ("Business", 45, "Mid-period conversation fixture"),
            ("Education", 80, "Older conversation fixture"),
            ("Economy", 40, "Four-comment threshold fixture"),
        ]
        scenario_perceptions: list[tuple[Perception, int, str]] = []
        for topic_name, age_days, label in scenario_specs:
            created_at = now - timedelta(days=age_days, hours=2)
            perception = Perception(
                user_id=demo_owner.id,
                topic_id=topics[topic_name].id,
                body=(
                    f"{label}: a seeded proposition about {TOPIC_FOCUS[topic_name]}. "
                    "This fixture exists to exercise Perception Intelligence and Profile Intelligence."
                ),
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(perception)
            scenario_perceptions.append((perception, age_days, topic_name))
        await db.flush()

        # Zero-comment perception: 9 interaction actors, but zero commenters.
        # The Perception Intelligence audience must therefore report zero
        # conversation participants, even though creator metrics can see events.
        zero_perception = scenario_perceptions[0][0]
        for position, actor in enumerate(users[1:10]):
            event_time = zero_perception.created_at + timedelta(hours=1 + position)
            if event_time > now:
                event_time = now - timedelta(minutes=position + 1)
            db.add(Like(
                user_id=actor.id,
                perception_id=zero_perception.id,
                created_at=event_time,
                updated_at=event_time,
            ))
            day = event_time.replace(hour=0, minute=0, second=0, microsecond=0)
            db.add(PerceptionInteraction(
                actor_user_id=actor.id,
                perception_id=zero_perception.id,
                event_type="VIEW",
                occurred_on=day,
                created_at=event_time,
            ))

        # Rich conversation fixtures: six distinct commenters in each of three
        # time buckets. The shared "access" theme makes cross-Topic recurrence
        # deterministic; role and geography come from the seeded participants.
        comment_specs = [
            (scenario_perceptions[1][0], users[1:7], "access"),
            (scenario_perceptions[2][0], users[7:13], "access"),
            (scenario_perceptions[3][0], users[13:19], "access"),
        ]
        fixture_bodies = [
            "I agree that access is the central issue in my experience.",
            "I have seen a different outcome, especially around access.",
            "What evidence would help us compare access across communities?",
            "This is useful, but access depends on local conditions.",
            "The proposal could improve access if implementation is practical.",
            "I am concerned that access may remain uneven.",
        ]
        for perception, commenters, shared_theme in comment_specs:
            parents: list[Comment] = []
            for position, commenter in enumerate(commenters):
                comment_time = perception.created_at + timedelta(hours=3 + position)
                comment = Comment(
                    user_id=commenter.id,
                    perception_id=perception.id,
                    body=fixture_bodies[position],
                    created_at=comment_time,
                    updated_at=comment_time,
                )
                db.add(comment)
                parents.append(comment)
            await db.flush()
            # Add two replies to prove reply comments also participate in the
            # comment/intelligence pipeline.
            for position, parent in enumerate(parents[:2]):
                commenter = users[19 + position]
                reply_time = parent.created_at + timedelta(hours=2)
                db.add(Comment(
                    user_id=commenter.id,
                    perception_id=perception.id,
                    parent_comment_id=parent.id,
                    body="That matches what I have observed about access too.",
                    created_at=reply_time,
                    updated_at=reply_time,
                ))

        threshold_perception = scenario_perceptions[4][0]
        for position, commenter in enumerate(users[20:24]):
            comment_time = threshold_perception.created_at + timedelta(hours=3 + position)
            db.add(Comment(
                user_id=commenter.id,
                perception_id=threshold_perception.id,
                body="A small-sample threshold fixture for analytics testing.",
                created_at=comment_time,
                updated_at=comment_time,
            ))
        await db.flush()

        # Seed deterministic analyzed semantic evidence for the rich fixtures
        # and all ordinary seeded comments. This makes frontend analytics tests
        # independent of the external LLM provider and its rate limits.
        all_comment_rows = (
            await db.execute(
                select(Comment.id, Comment.perception_id, Comment.created_at)
                .where(Comment.perception_id.in_([p.id for p in perceptions] + [p.id for p, _, _ in scenario_perceptions]))
            )
        ).all()
        semantic_themes = ["access", "trust", "adoption", "implementation"]
        for position, (comment_id, _perception_id, comment_time) in enumerate(all_comment_rows):
            db.add(CommentIntelligence(
                comment_id=comment_id,
                status="analyzed",
                sentiment=["positive", "neutral", "mixed", "negative"][position % 4],
                stance=["supportive", "challenging", "mixed", "unclear"][position % 4],
                themes=[semantic_themes[position % len(semantic_themes)]],
                is_question=position % 5 == 0,
                has_concern=position % 4 == 3,
                agreement_signal=position % 4 == 0,
                disagreement_signal=position % 4 == 1,
                quality_score=0.9,
                model_version="demo-seed-v1",
                analyzed_at=comment_time,
            ))

        await db.flush()

        # ------------------------------------------------------------------
        # VIEW / SHARE events. These are the explicit analytics events used by
        # /api/analytics/overview. They are spread across the current period.
        # ------------------------------------------------------------------
        for index, perception in enumerate(perceptions):
            current = perception.created_at >= now - timedelta(days=30)
            if not current:
                event_count = random.randint(1, 3)
            else:
                event_count = random.randint(3, 10)

            actors = random.sample(users, k=min(event_count, len(users)))
            for position, actor in enumerate(actors):
                event_time = perception.created_at + timedelta(
                    hours=random.randint(1, 48), minutes=random.randint(0, 59)
                )
                if event_time > now:
                    event_time = now - timedelta(minutes=position + 1)
                day = event_time.replace(hour=0, minute=0, second=0, microsecond=0)
                event_type = "SHARE" if (index + position) % 5 == 0 else "VIEW"
                db.add(
                    PerceptionInteraction(
                        actor_user_id=actor.id,
                        perception_id=perception.id,
                        event_type=event_type,
                        occurred_on=day,
                        created_at=event_time,
                    )
                )

        await db.commit()

        print("\nDemo seed complete.")
        print(f"Users: {len(users)}")
        print(f"Perceptions: {len(perceptions) + len(scenario_perceptions)}")
        print("Likes/comments/views/shares: generated across all perceptions")
        print(f"Analytics accounts: {len(analytics_users)}")
        print("Deterministic intelligence fixtures: zero-comment, rich-conversation, threshold, and longitudinal")
        print("Subscription fixtures: demo11 expired, demo12 past_due-within-period, demo13 past_due-expired")
        print("\nFrontend test accounts:")
        print("  demo01@example.com  / Demo1234!  (Professional analytics)")
        print("  demo04@example.com  / Demo1234!  (Research analytics)")
        print("  demo05@example.com  / Demo1234!  (Business analytics)")
        print("  demo09@example.com  / Demo1234!  (Free / analytics gate test)")


if __name__ == "__main__":
    asyncio.run(seed_demo())
