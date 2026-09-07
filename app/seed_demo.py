"""Populate a realistic demo dataset for frontend + analytics testing.

Usage:
    python -m app.seed_demo

Or, when running the API inside Docker:
    docker compose exec api python -m app.seed_demo

The seed is deterministic and safe to re-run for the demo accounts.

Every run first removes the existing demo dataset belonging to accounts whose
email starts with ``demo`` and uses either ``@perception.local`` or
``@example.com``. It then recreates the complete demo dataset using the
current application schema.

Production/reference users, topics and plans are left untouched.

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
    (
        "Amina Hassan",
        "Product Manager",
        "Digital products and customer research",
    ),
    (
        "Brian Otieno",
        "Software Engineer",
        "Applied technology and AI adoption",
    ),
    (
        "Grace Wanjiku",
        "Teacher",
        "Learning outcomes and education access",
    ),
    (
        "Daniel Mwangi",
        "Business Analyst",
        "SME growth and market intelligence",
    ),
    (
        "Faith Njeri",
        "Public Health Specialist",
        "Community health and prevention",
    ),
    (
        "Kevin Ouma",
        "Researcher",
        "Data, evidence and social research",
    ),
    (
        "Mercy Achieng",
        "Economist",
        "Household economics and consumer behaviour",
    ),
    (
        "Samuel Kibet",
        "Entrepreneur",
        "Retail, logistics and local markets",
    ),
    (
        "Esther Wambui",
        "UX Designer",
        "Human behaviour and digital experiences",
    ),
    (
        "Joseph Kamau",
        "Data Analyst",
        "Decision intelligence and analytics",
    ),
    (
        "Lilian Atieno",
        "Journalist",
        "Society, media and public opinion",
    ),
    (
        "Peter Kariuki",
        "Agribusiness Consultant",
        "Food systems and rural markets",
    ),
    (
        "Ruth Muthoni",
        "Nurse",
        "Health education and patient experience",
    ),
    (
        "Mark Kiptoo",
        "Developer",
        "Developer tools and technology adoption",
    ),
    (
        "Irene Chebet",
        "Lecturer",
        "Higher education and workforce readiness",
    ),
    (
        "Alex Maina",
        "Founder",
        "Startups, product-market fit and innovation",
    ),
    (
        "Susan Adhiambo",
        "Community Organizer",
        "Community development and inclusion",
    ),
    (
        "Victor Omondi",
        "Financial Advisor",
        "Personal finance and economic resilience",
    ),
    (
        "Naomi Jepchirchir",
        "Scientist",
        "Science communication and public trust",
    ),
    (
        "John Mutua",
        "Sports Coach",
        "Youth sport and performance",
    ),
    (
        "Caroline Wairimu",
        "Marketing Strategist",
        "Brand perception and consumer behaviour",
    ),
    (
        "Eric Odhiambo",
        "Cybersecurity Analyst",
        "Digital trust and online safety",
    ),
    (
        "Miriam Kilonzo",
        "Policy Researcher",
        "Public policy and social outcomes",
    ),
    (
        "Collins Barasa",
        "Operations Manager",
        "Supply chains and operational efficiency",
    ),
    (
        "Diana Akinyi",
        "Psychologist",
        "Wellbeing, behaviour and community support",
    ),
    (
        "Felix Njoroge",
        "Architect",
        "Cities, housing and sustainable development",
    ),
    (
        "Beatrice Nyambura",
        "HR Specialist",
        "Workplace culture and future skills",
    ),
    (
        "George Were",
        "Teacher",
        "Digital learning and classroom innovation",
    ),
    (
        "Ann Waithera",
        "Consultant",
        "Organisational strategy and transformation",
    ),
    (
        "David Kiplangat",
        "Farmer",
        "Agriculture, climate and local economies",
    ),
]


# Structured professional identity used by the Stage 4 taxonomy.
#
# Each entry maps the legacy demo profession to:
#   1. one or more industry codes
#   2. one or more professional role codes
#
# The first role code becomes the primary professional role.
DEMO_IDENTITY = {
    "Product Manager": (
        ["technology"],
        ["product_manager"],
    ),
    "Software Engineer": (
        ["technology"],
        ["software_engineer"],
    ),
    "Teacher": (
        ["education"],
        ["teacher"],
    ),
    "Business Analyst": (
        ["business"],
        ["business_analyst"],
    ),
    "Public Health Specialist": (
        ["healthcare"],
        ["public_health_specialist"],
    ),
    "Researcher": (
        ["science"],
        ["research_scientist"],
    ),
    "Economist": (
        ["finance"],
        ["economist"],
    ),
    "Entrepreneur": (
        ["business"],
        ["entrepreneur"],
    ),
    "UX Designer": (
        ["technology"],
        ["ux_designer"],
    ),
    "Data Analyst": (
        ["technology"],
        ["data_scientist"],
    ),
    "Journalist": (
        ["media"],
        ["journalist"],
    ),
    "Agribusiness Consultant": (
        ["agriculture", "business"],
        ["agronomist", "business_consultant"],
    ),
    "Nurse": (
        ["healthcare"],
        ["nurse"],
    ),
    "Developer": (
        ["technology"],
        ["web_developer"],
    ),
    "Lecturer": (
        ["education"],
        ["lecturer"],
    ),
    "Founder": (
        ["business", "technology"],
        ["founder", "product_manager"],
    ),
    "Community Organizer": (
        ["nonprofit"],
        ["social_worker"],
    ),
    "Financial Advisor": (
        ["finance"],
        ["financial_advisor"],
    ),
    "Scientist": (
        ["science"],
        ["research_scientist"],
    ),
    "Sports Coach": (
        ["sports"],
        ["coach"],
    ),
    "Marketing Strategist": (
        ["business"],
        ["business_consultant"],
    ),
    "Cybersecurity Analyst": (
        ["technology", "security"],
        ["cybersecurity_specialist", "security_analyst"],
    ),
    "Policy Researcher": (
        ["government", "science"],
        ["policy_analyst", "research_scientist"],
    ),
    "Operations Manager": (
        ["business", "logistics"],
        ["operations_manager", "logistics_manager"],
    ),
    "Psychologist": (
        ["healthcare"],
        ["psychologist"],
    ),
    "Architect": (
        ["construction"],
        ["architect"],
    ),
    "HR Specialist": (
        ["professional_services"],
        ["human_resources_specialist"],
    ),
    "Consultant": (
        ["professional_services"],
        ["management_consultant"],
    ),
    "Farmer": (
        ["agriculture"],
        ["farmer"],
    ),
}


TOPIC_FOCUS = {
    "Business": ("how businesses understand customers, markets and growth"),
    "Technology": ("how people adopt technology and how it changes everyday work"),
    "Education": ("how learning systems affect skills, opportunity and outcomes"),
    "Health": ("how communities understand health, prevention and wellbeing"),
    "Economy": ("how economic conditions affect households, prices and decisions"),
    "Science": ("how people understand scientific evidence and discovery"),
    "Culture": ("how culture shapes behaviour, identity and community life"),
    "Society": ("how social changes affect communities and relationships"),
    "Lifestyle": ("how people balance work, wellbeing and everyday choices"),
    "Sports": ("how sport affects youth, health and community identity"),
    "Religion": ("how faith and spirituality shape community life"),
    "Politics": ("how people perceive public policy and political change"),
}


def weighted_topic_names() -> list[str]:
    """Expand weighted topic configuration into a deterministic list."""
    names: list[str] = []

    for name, weight in TOPIC_WEIGHTS.items():
        names.extend([name] * weight)

    return names


def perception_body(
    topic: str,
    index: int,
    current: bool,
) -> str:
    """Generate realistic but deterministic demo perception content."""

    phase = (
        "Recent community discussions" if current else "Earlier community discussions"
    )

    focus = TOPIC_FOCUS[topic]

    variants = [
        (
            f"{phase} suggest that {focus}. "
            "What are people actually experiencing on the ground?"
        ),
        (
            f"My observation is that {focus}. "
            "I would like to compare this perspective with others."
        ),
        (
            f"A recurring question is whether {focus}. "
            "Different communities may be seeing very different outcomes."
        ),
        (
            f"From conversations in my work, I keep noticing that {focus}. "
            "The pattern deserves closer attention."
        ),
        (
            f"There seems to be a growing perception that {focus}. "
            "More voices could help us understand why."
        ),
    ]

    return variants[index % len(variants)]


async def reset_demo_data(db) -> dict[str, int]:
    """Reset all known data belonging to the demo accounts.

    Only accounts matching the demo email patterns are affected.

    Reference/application data such as Topic and Plan is deliberately
    preserved.

    The cleanup is explicit rather than depending exclusively on ORM/database
    cascade configuration. This makes repeated seed runs deterministic even
    when relationship definitions evolve.
    """

    demo_user_ids = (
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

    if not demo_user_ids:
        return {
            "users": 0,
            "perceptions": 0,
            "likes": 0,
            "comments": 0,
            "interactions": 0,
            "follows": 0,
            "topic_follows": 0,
            "analytics_topics": 0,
            "subscriptions": 0,
            "verification_applications": 0,
        }

    # --------------------------------------------------------------
    # Identify perceptions authored by demo users before deleting
    # dependent interaction data.
    # --------------------------------------------------------------
    demo_perception_ids = (
        (
            await db.execute(
                select(Perception.id).where(Perception.user_id.in_(demo_user_ids))
            )
        )
        .scalars()
        .all()
    )

    # --------------------------------------------------------------
    # Perception interactions
    #
    # Two cases matter:
    #
    # 1. The demo user is the actor.
    # 2. The event belongs to a perception authored by a demo user.
    #
    # We remove both.
    # --------------------------------------------------------------
    interaction_result = await db.execute(
        delete(PerceptionInteraction).where(
            (PerceptionInteraction.actor_user_id.in_(demo_user_ids))
            | (
                PerceptionInteraction.perception_id.in_(demo_perception_ids)
                if demo_perception_ids
                else False
            )
        )
    )

    # --------------------------------------------------------------
    # Likes made by demo users.
    #
    # This includes likes on perceptions belonging to other users.
    # --------------------------------------------------------------
    like_by_user_result = await db.execute(
        delete(Like).where(Like.user_id.in_(demo_user_ids))
    )

    # Likes on demo-authored perceptions.
    like_on_perception_result = 0

    if demo_perception_ids:
        like_on_perception_result = (
            await db.execute(
                delete(Like).where(Like.perception_id.in_(demo_perception_ids))
            )
        ).rowcount or 0

    # --------------------------------------------------------------
    # Comments made by demo users.
    # --------------------------------------------------------------
    comment_by_user_result = await db.execute(
        delete(Comment).where(Comment.user_id.in_(demo_user_ids))
    )

    # Comments on demo-authored perceptions.
    comment_on_perception_result = 0

    if demo_perception_ids:
        comment_on_perception_result = (
            await db.execute(
                delete(Comment).where(Comment.perception_id.in_(demo_perception_ids))
            )
        ).rowcount or 0

    # --------------------------------------------------------------
    # User-to-user follows.
    #
    # Both directions are demo-owned:
    #   demo -> anyone
    #   anyone -> demo
    #
    # This prevents stale relationships from affecting the next seed.
    # --------------------------------------------------------------
    follow_result = await db.execute(
        delete(Follow).where(
            (Follow.follower_id.in_(demo_user_ids))
            | (Follow.followed_id.in_(demo_user_ids))
        )
    )

    # --------------------------------------------------------------
    # Topic follows.
    # --------------------------------------------------------------
    topic_follow_result = await db.execute(
        delete(TopicFollow).where(TopicFollow.user_id.in_(demo_user_ids))
    )

    # --------------------------------------------------------------
    # Analytics topic selections.
    # --------------------------------------------------------------
    analytics_topic_result = await db.execute(
        delete(AnalyticsTopic).where(AnalyticsTopic.user_id.in_(demo_user_ids))
    )

    # --------------------------------------------------------------
    # Subscriptions.
    # --------------------------------------------------------------
    subscription_result = await db.execute(
        delete(Subscription).where(Subscription.user_id.in_(demo_user_ids))
    )

    # --------------------------------------------------------------
    # Verification applications.
    # --------------------------------------------------------------
    verification_result = await db.execute(
        delete(VerificationApplication).where(
            VerificationApplication.user_id.in_(demo_user_ids)
        )
    )

    # --------------------------------------------------------------
    # Perceptions authored by demo users.
    # --------------------------------------------------------------
    perception_result = 0

    if demo_perception_ids:
        perception_result = (
            await db.execute(
                delete(Perception).where(Perception.id.in_(demo_perception_ids))
            )
        ).rowcount or 0

    # --------------------------------------------------------------
    # Finally remove the demo users.
    # --------------------------------------------------------------
    user_result = await db.execute(delete(User).where(User.id.in_(demo_user_ids)))

    return {
        "users": user_result.rowcount or 0,
        "perceptions": perception_result,
        "likes": ((like_by_user_result.rowcount or 0) + like_on_perception_result),
        "comments": (
            (comment_by_user_result.rowcount or 0) + comment_on_perception_result
        ),
        "interactions": interaction_result.rowcount or 0,
        "follows": follow_result.rowcount or 0,
        "topic_follows": topic_follow_result.rowcount or 0,
        "analytics_topics": analytics_topic_result.rowcount or 0,
        "subscriptions": subscription_result.rowcount or 0,
        "verification_applications": (verification_result.rowcount or 0),
    }


async def seed_demo() -> None:
    """Reset and recreate the complete deterministic demo dataset."""

    random.seed(SEED)
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # ==============================================================
        # RESET EXISTING DEMO DATA
        # ==============================================================

        removed = await reset_demo_data(db)

        if removed["users"]:
            print("\nExisting demo dataset reset:")
            print(f"  Users: {removed['users']}")
            print(f"  Perceptions: {removed['perceptions']}")
            print(f"  Likes: {removed['likes']}")
            print(f"  Comments: {removed['comments']}")
            print(f"  Interactions: {removed['interactions']}")
            print(f"  Follows: {removed['follows']}")
            print(f"  Topic follows: {removed['topic_follows']}")
            print("  Analytics topics: " f"{removed['analytics_topics']}")
            print("  Subscriptions: " f"{removed['subscriptions']}")
            print(
                "  Verification applications: "
                f"{removed['verification_applications']}"
            )
        else:
            print("\nNo existing demo dataset found. " "Creating fresh demo data.")

        # ==============================================================
        # REFERENCE DATA
        #
        # Topics and plans belong to the application, not this seed.
        # They are therefore loaded and preserved.
        # ==============================================================

        topics = {
            topic.name: topic
            for topic in (await db.execute(select(Topic))).scalars().all()
        }

        if not topics:
            raise RuntimeError("No topics found. Run `python -m app.seed` first.")

        plans = {
            plan.code: plan for plan in (await db.execute(select(Plan))).scalars().all()
        }

        for required in (
            "free",
            "professional",
            "research",
            "business",
        ):
            if required not in plans:
                raise RuntimeError(
                    f"Missing plan `{required}`. " "Run `python -m app.seed` first."
                )

        # ==============================================================
        # USERS
        # ==============================================================

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

        for index, (name, profession, focus) in enumerate(
            PROFILES,
            start=1,
        ):
            country_code, region, city = COUNTRIES[(index - 1) % len(COUNTRIES)]

            primary_name = primary_topics[(index - 1) % len(primary_topics)]

            primary_topic = topics.get(primary_name)

            specialty_names = [primary_name]

            for extra in (
                "Business",
                "Technology",
                "Education",
                "Health",
                "Economy",
            ):
                if (
                    extra != primary_name
                    and len(specialty_names) < 3
                    and extra in topics
                ):
                    specialty_names.append(extra)

            # User.analytics_specialties stores AnalyticsTopic IDs,
            # not topic names.
            specialties = [topics[name].id for name in specialty_names]

            # ----------------------------------------------------------
            # Structured professional identity.
            # ----------------------------------------------------------

            industry_codes, role_codes = DEMO_IDENTITY.get(
                profession,
                ([], []),
            )

            primary_role = role_codes[0] if role_codes else None

            # First 12 users are deliberately verified demo
            # professionals.
            is_verified = index <= 12

            # Do not silently create an invalid role-specific badge.
            verification_badge = None

            if is_verified and primary_role and primary_role in ROLE_MAP:
                verification_badge = ROLE_MAP[primary_role]["icon"]

            user = User(
                name=name,
                role="USER",
                email=f"demo{index:02d}@example.com",
                password_hash=hash_password(DEMO_PASSWORD),
                # Legacy / compatibility identity fields.
                profession=profession,
                professional_focus=focus,
                # Structured professional identity.
                professional_industries=industry_codes,
                professional_roles=role_codes,
                primary_professional_role=primary_role,
                # Only verified demo users receive verified roles.
                verified_professional_roles=(role_codes if is_verified else []),
                country_code=country_code,
                region=region,
                city=city,
                analytics_specialties=specialties,
                primary_analytics_topic_id=(
                    primary_topic.id if primary_topic else None
                ),
                verification_status=("VERIFIED" if is_verified else "NOT_APPLIED"),
                verification_badge=verification_badge,
                bio=("Demo participant interested in " f"{focus.lower()}."),
            )

            users.append(user)
            db.add(user)

        await db.flush()

        # ==============================================================
        # SUBSCRIPTIONS + ANALYTICS TOPICS + VERIFICATION
        # ==============================================================

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
                        current_period_end=(now + timedelta(days=45)),
                        cancel_at_period_end=False,
                    )
                )

                selected_names = list(
                    dict.fromkeys(
                        [
                            primary_topics[index % len(primary_topics)],
                            "Business",
                            "Technology",
                            "Education",
                            "Health",
                            "Economy",
                        ]
                    )
                )

                selected_names = [name for name in selected_names if name in topics][
                    : plan.max_topics
                ]

                for topic_name in selected_names:
                    db.add(
                        AnalyticsTopic(
                            user_id=user.id,
                            topic_id=topics[topic_name].id,
                        )
                    )

                # ------------------------------------------------------
                # Approved professional verification records.
                # ------------------------------------------------------

                if user.verification_status == "VERIFIED":
                    verification_badge = None

                    if (
                        user.primary_professional_role
                        and user.primary_professional_role in ROLE_MAP
                    ):
                        verification_badge = ROLE_MAP[user.primary_professional_role][
                            "icon"
                        ]

                    db.add(
                        VerificationApplication(
                            user_id=user.id,
                            # Legacy compatibility fields.
                            profession=(user.profession or "Professional"),
                            focus=(user.professional_focus or "General research"),
                            # Structured verification identity.
                            industry_codes=(user.professional_industries or []),
                            professional_role_codes=(user.professional_roles or []),
                            primary_professional_role=(user.primary_professional_role),
                            primary_topic_id=(user.primary_analytics_topic_id),
                            requested_topic_ids=[
                                topics[name].id for name in selected_names
                            ],
                            evidence=(
                                "Synthetic demo evidence " "for frontend testing."
                            ),
                            status="APPROVED",
                            badge=verification_badge,
                            reviewer_note="Demo seed record.",
                        )
                    )

        # ==============================================================
        # TOPIC FOLLOWS
        # ==============================================================

        for user in users:
            follow_topics = random.sample(
                list(topics.values()),
                k=min(4, len(topics)),
            )

            for topic in follow_topics:
                db.add(
                    TopicFollow(
                        user_id=user.id,
                        topic_id=topic.id,
                    )
                )

        # ==============================================================
        # USER FOLLOWS
        # ==============================================================

        for user in users:
            candidates = [candidate for candidate in users if candidate.id != user.id]

            for followed in random.sample(
                candidates,
                k=min(5, len(candidates)),
            ):
                db.add(
                    Follow(
                        follower_id=user.id,
                        followed_id=followed.id,
                    )
                )

        await db.flush()

        # ==============================================================
        # PERCEPTIONS
        #
        # 70 previous-period + 250 current-period records.
        #
        # The current period is intentionally busier so growth,
        # momentum and opportunity cards have meaningful data.
        # ==============================================================

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

            body = perception_body(
                topic_name,
                index,
                current,
            )

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

        # ==============================================================
        # LIKES + COMMENTS
        #
        # Interaction counts vary by topic to create visible
        # differences in signal strength and opportunity ranking.
        # ==============================================================

        for index, perception in enumerate(perceptions):
            topic_name = next(
                name
                for name, topic in topics.items()
                if topic.id == perception.topic_id
            )

            if topic_name in {
                "Business",
                "Technology",
                "Education",
            }:
                like_count = random.randint(6, 13)
                comment_count = random.randint(2, 5)

            elif topic_name in {
                "Health",
                "Economy",
                "Science",
            }:
                like_count = random.randint(4, 10)
                comment_count = random.randint(1, 4)

            else:
                like_count = random.randint(2, 7)
                comment_count = random.randint(0, 3)

            # ----------------------------------------------------------
            # Likes
            # ----------------------------------------------------------

            likers = random.sample(
                users,
                k=min(
                    like_count,
                    len(users),
                ),
            )

            for position, liker in enumerate(likers):
                like_time = perception.created_at + timedelta(
                    hours=random.randint(1, 72),
                    minutes=random.randint(0, 59),
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

            # ----------------------------------------------------------
            # Comments
            # ----------------------------------------------------------

            commenters = (
                random.sample(
                    users,
                    k=min(
                        max(1, comment_count),
                        len(users),
                    ),
                )
                if comment_count
                else []
            )

            for position, commenter in enumerate(commenters[:comment_count]):
                comment_time = perception.created_at + timedelta(
                    hours=random.randint(1, 96),
                    minutes=random.randint(0, 59),
                )

                if comment_time > now:
                    comment_time = now - timedelta(minutes=position + 1)

                db.add(
                    Comment(
                        user_id=commenter.id,
                        perception_id=perception.id,
                        body=[
                            (
                                "Interesting perspective — "
                                "I have seen something similar."
                            ),
                            (
                                "This is useful. I would like "
                                "to see how it varies by location."
                            ),
                            (
                                "I agree, although my experience "
                                "has been slightly different."
                            ),
                            (
                                "What evidence would help us "
                                "test this perception further?"
                            ),
                            ("This could be a useful signal " "for decision-making."),
                        ][(index + position) % 5],
                        created_at=comment_time,
                        updated_at=comment_time,
                    )
                )

        await db.flush()

        # ==============================================================
        # VIEW / SHARE EVENTS
        #
        # These are the explicit analytics events used by
        # /api/analytics/overview.
        # ==============================================================

        for index, perception in enumerate(perceptions):
            current = perception.created_at >= now - timedelta(days=30)

            if not current:
                event_count = random.randint(1, 3)
            else:
                event_count = random.randint(3, 10)

            actors = random.sample(
                users,
                k=min(
                    event_count,
                    len(users),
                ),
            )

            for position, actor in enumerate(actors):
                event_time = perception.created_at + timedelta(
                    hours=random.randint(1, 48),
                    minutes=random.randint(0, 59),
                )

                if event_time > now:
                    event_time = now - timedelta(minutes=position + 1)

                day = event_time.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )

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

        # ==============================================================
        # FINAL COMMIT
        # ==============================================================

        await db.commit()

        # ==============================================================
        # REPORT
        # ==============================================================

        print("\nDemo seed complete.")
        print("----------------------------------------")
        print(f"Demo users recreated: {len(users)}")
        print(f"Perceptions created: {len(perceptions)}")
        print("Likes/comments/views/shares: " "generated across all perceptions")
        print(f"Analytics accounts: {len(analytics_users)}")

        print("\nProfessional identity:")
        print("  Verified demo professionals: 12")
        print("  Structured industries/roles: populated")
        print("  Role-specific verification badges: populated")

        print("\nFrontend test accounts:")
        print("  demo01@example.com  / Demo1234!  " "(Professional analytics)")
        print("  demo04@example.com  / Demo1234!  " "(Research analytics)")
        print("  demo05@example.com  / Demo1234!  " "(Business analytics)")
        print("  demo09@example.com  / Demo1234!  " "(Free / analytics gate test)")

        print("\nRe-run behavior:")
        print("  Existing demo users/data: RESET")
        print("  Reference topics/plans: PRESERVED")
        print("  Production/reference users: PRESERVED")


if __name__ == "__main__":
    asyncio.run(seed_demo())
