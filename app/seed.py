# app/seed.py
"""
Seeds baseline reference data — topics and motivational quotes — so a fresh
`docker compose up` has something to look at immediately. Safe to re-run;
skips anything that already exists.

Usage: docker compose exec api python -m app.seed
"""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Motivation, Topic

TOPICS = [
    ("Technology", "Software, hardware, and the tools shaping how we build."),
    ("Politics", "Governance, policy, and public life."),
    ("Culture", "Art, music, film, and the stories we tell."),
    ("Business", "Markets, startups, and the world of work."),
    ("Sports", "Competition, teams, and the games we follow."),
    ("Science", "Discovery, research, and how the world works."),
    ("Health", "Wellbeing, medicine, and how we take care of ourselves."),
    ("Education", "Learning, teaching, and how knowledge spreads."),
]

MOTIVATIONS = [
    "Every perspective is a piece of the whole picture — share yours.",
    "The view from where you stand is worth more than you think.",
    "Understanding starts with listening to a different vantage point.",
    "One topic, a thousand angles — what's yours today?",
    "Your take might be the missing piece for someone else.",
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(select(Topic.name))).scalars().all()
        existing_names = set(existing)

        for name, description in TOPICS:
            if name not in existing_names:
                db.add(Topic(name=name, description=description))

        await db.flush()

        existing_motivations_count = (await db.execute(select(Motivation.id))).scalars().all()
        if not existing_motivations_count:
            for body in MOTIVATIONS:
                db.add(Motivation(body=body))

        await db.commit()
    print(f"Seeded {len(TOPICS)} topics and {len(MOTIVATIONS)} motivations (skipping any that already existed).")


if __name__ == "__main__":
    asyncio.run(seed())
