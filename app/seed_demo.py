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
from app.models.models import (
    AnalyticsTopic,
    Comment,
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

            user = User(
                name=name,
                role="USER",
                email=f"demo{index:02d}@example.com",
                password_hash=hash_password(DEMO_PASSWORD),
                profession=profession,
                professional_focus=focus,
                country_code=country_code,
                region=region,
                city=city,
                analytics_specialties=specialties,
                primary_analytics_topic_id=primary_topic.id if primary_topic else None,
                verification_status="VERIFIED" if index <= 12 else "NOT_APPLIED",
                verification_badge="PROFESSIONAL" if index <= 12 else None,
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
                            focus=user.professional_focus or "General research",
                            primary_topic_id=user.primary_analytics_topic_id,
                            requested_topic_ids=[
                                topics[name].id for name in selected_names
                            ],
                            evidence="Synthetic demo evidence for frontend testing.",
                            status="APPROVED",
                            badge="PROFESSIONAL",
                            reviewer_note="Demo seed record.",
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
        print(f"Perceptions: {len(perceptions)}")
        print("Likes/comments/views/shares: generated across all perceptions")
        print(f"Analytics accounts: {len(analytics_users)}")
        print("\nFrontend test accounts:")
        print("  demo01@example.com  / Demo1234!  (Professional analytics)")
        print("  demo04@example.com  / Demo1234!  (Research analytics)")
        print("  demo05@example.com  / Demo1234!  (Business analytics)")
        print("  demo09@example.com  / Demo1234!  (Free / analytics gate test)")


if __name__ == "__main__":
    asyncio.run(seed_demo())
