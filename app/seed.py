# app/seed.py
"""
Seeds baseline reference data — topics and motivational quotes — so a fresh
`docker compose up` has something to look at immediately. Safe to re-run;
synchronizes text or image changes for existing entries and adds new ones.

Usage: docker compose exec api python -m app.seed
"""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Motivation, Topic

# Synchronized and matching your authentic Laravel seed collection including image_urls
TOPICS = [
    {
        "name": "Business",
        "description": "Exploring diverse perceptions of business practices, strategies, and market trends.",
        "image_url": "/storage/topics/business.jpg",
    },
    {
        "name": "Culture",
        "description": "Understanding how different cultures perceive and interpret the world around them.",
        "image_url": "/storage/topics/culture.jpg",
    },
    {
        "name": "Education",
        "description": "Exploring diverse perceptions of education systems, learning approaches, and academic growth.",
        "image_url": "/storage/topics/education.webp",
    },
    {
        "name": "Health",
        "description": "Understanding how different groups perceive health, wellness, and medical practices.",
        "image_url": "/storage/topics/health.png",
    },
    {
        "name": "Science",
        "description": "Exploring diverse perceptions of scientific discoveries, theories, and their implications.",
        "image_url": "/storage/topics/science.avif",
    },
    {
        "name": "Sports",
        "description": "Understanding how different groups perceive sports, athleticism, and competition.",
        "image_url": "/storage/topics/sports.jpg",
    },
    {
        "name": "Technology",
        "description": "Exploring diverse perceptions of technology's impact and future.",
        "image_url": "/storage/topics/technology.jpg",
    },
    {
        "name": "Religion",
        "description": "Sharing and understanding different perceptions of faith, spirituality, and religious practices.",
        "image_url": "/storage/topics/Religion.png",
    },
    {
        "name": "Politics",
        "description": "Examining varied perceptions of political events, ideologies, and figures.",
        "image_url": "/storage/topics/politics.jpg",
    },
    {
        "name": "Economy",
        "description": "Understanding how different groups perceive economic trends, policies, and their personal impact.",
        "image_url": "/storage/topics/economy.png",
    },
    {
        "name": "Society",
        "description": "Discussing varying perceptions of social norms, issues, and community dynamics.",
        "image_url": "/storage/topics/Society.webp",
    },
    {
        "name": "Lifestyle",
        "description": "Exploring different perceptions of what constitutes a fulfilling or aspirational lifestyle.",
        "image_url": "/storage/topics/lifestyle.avif",
    },
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
        # Fetch full topic instances to inspect descriptions and image URLs
        result = await db.execute(select(Topic))
        existing_topics = {t.name: t for t in result.scalars().all()}

        inserted_count = 0
        updated_count = 0

        for item in TOPICS:
            name = item["name"]
            desc = item["description"]
            img = item["image_url"]

            if name in existing_topics:
                # Laravel style: check if content has mutated "in or out" and sync it
                existing_topic = existing_topics[name]
                if existing_topic.description != desc or existing_topic.image_url != img:
                    existing_topic.description = desc
                    existing_topic.image_url = img
                    updated_count += 1
            else:
                # Insert entirely new records
                db.add(Topic(name=name, description=desc, image_url=img))
                inserted_count += 1

        await db.flush()

        # Seed motivations only if table is completely empty
        motivation_result = await db.execute(select(Motivation.id))
        has_motivations = motivation_result.scalars().first() is not None
        
        if not has_motivations:
            for body in MOTIVATIONS:
                db.add(Motivation(body=body))

        await db.commit()
        
    print(
        f"Seeding complete! Topics: {inserted_count} added, {updated_count} updated. "
        f"Motivations checked."
    )


if __name__ == "__main__":
    asyncio.run(seed())
