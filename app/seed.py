"""Seed baseline reference data for Perception.

This module owns database synchronization for static application
reference data.

It seeds:
- topics
- plans
- Stripe price IDs associated with plans
- motivational quotes

It does not seed:
- users
- subscriptions
- perceptions
- comments
- likes
- follows
- analytics events
- demo accounts

Usage:
    docker compose exec api python -m app.seed

The operation is safe to re-run. Existing reference records are
synchronized with the values defined in app.seed_data.reference.
"""

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.models import Motivation, Plan, Topic
from app.seed_data.reference import MOTIVATIONS, PLANS, TOPICS


async def seed() -> None:
    """Synchronize baseline reference data."""

    async with AsyncSessionLocal() as db:
        # ------------------------------------------------------------------
        # Topics
        # ------------------------------------------------------------------
        result = await db.execute(select(Topic))

        existing_topics = {topic.name: topic for topic in result.scalars().all()}

        topics_inserted = 0
        topics_updated = 0

        for item in TOPICS:
            name = item["name"]
            description = item["description"]
            image_url = item["image_url"]

            existing_topic = existing_topics.get(name)

            if existing_topic is None:
                db.add(
                    Topic(
                        name=name,
                        description=description,
                        image_url=image_url,
                    )
                )
                topics_inserted += 1
                continue

            if (
                existing_topic.description != description
                or existing_topic.image_url != image_url
            ):
                existing_topic.description = description
                existing_topic.image_url = image_url
                topics_updated += 1

        await db.flush()

        # ------------------------------------------------------------------
        # Plans
        # ------------------------------------------------------------------
        result = await db.execute(select(Plan))

        existing_plans = {plan.code: plan for plan in result.scalars().all()}

        settings = get_settings()

        stripe_prices = {
            "professional": getattr(
                settings,
                "STRIPE_PRICE_PROFESSIONAL",
                "",
            ),
            "research": getattr(
                settings,
                "STRIPE_PRICE_RESEARCH",
                "",
            ),
            "business": getattr(
                settings,
                "STRIPE_PRICE_BUSINESS",
                "",
            ),
        }

        plans_inserted = 0
        plans_updated = 0

        for item in PLANS:
            plan_data = {
                **item,
                "stripe_price_id": stripe_prices.get(item["code"]) or None,
            }

            existing_plan = existing_plans.get(item["code"])

            if existing_plan is None:
                db.add(Plan(**plan_data))
                plans_inserted += 1
                continue

            changed = False

            for key, value in plan_data.items():
                if getattr(existing_plan, key) != value:
                    setattr(existing_plan, key, value)
                    changed = True

            if changed:
                plans_updated += 1

        await db.flush()

        # ------------------------------------------------------------------
        # Motivations
        # ------------------------------------------------------------------
        motivation_result = await db.execute(select(Motivation.id).limit(1))

        has_motivations = motivation_result.scalar_one_or_none() is not None

        motivations_inserted = 0

        if not has_motivations:
            for body in MOTIVATIONS:
                db.add(Motivation(body=body))

            motivations_inserted = len(MOTIVATIONS)

        # ------------------------------------------------------------------
        # Commit
        # ------------------------------------------------------------------
        await db.commit()

    print(
        "Reference seeding complete. "
        f"Topics: {topics_inserted} added, {topics_updated} updated. "
        f"Plans: {plans_inserted} added, {plans_updated} updated. "
        f"Motivations: {motivations_inserted} added."
    )


if __name__ == "__main__":
    asyncio.run(seed())
