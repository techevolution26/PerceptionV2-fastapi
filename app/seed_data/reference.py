"""Reference seed data for Perception.

This module contains static baseline/reference data only.

It must not contain:
- users
- subscriptions
- perceptions
- comments
- engagement
- analytics events
- demo accounts
"""

TOPICS = [
    {
        "name": "Business",
        "description": (
            "Exploring diverse perceptions of business practices, "
            "strategies, and market trends."
        ),
        "image_url": "/storage/topics/business.jpg",
    },
    {
        "name": "Culture",
        "description": (
            "Understanding how different cultures perceive and "
            "interpret the world around them."
        ),
        "image_url": "/storage/topics/culture.jpg",
    },
    {
        "name": "Education",
        "description": (
            "Exploring diverse perceptions of education systems, "
            "learning approaches, and academic growth."
        ),
        "image_url": "/storage/topics/education.webp",
    },
    {
        "name": "Health",
        "description": (
            "Understanding how different groups perceive health, "
            "wellness, and medical practices."
        ),
        "image_url": "/storage/topics/health.png",
    },
    {
        "name": "Science",
        "description": (
            "Exploring diverse perceptions of scientific discoveries, "
            "theories, and their implications."
        ),
        "image_url": "/storage/topics/science.avif",
    },
    {
        "name": "Sports",
        "description": (
            "Understanding how different groups perceive sports, "
            "athleticism, and competition."
        ),
        "image_url": "/storage/topics/sports.jpg",
    },
    {
        "name": "Technology",
        "description": (
            "Exploring diverse perceptions of technology's impact " "and future."
        ),
        "image_url": "/storage/topics/technology.jpg",
    },
    {
        "name": "Religion",
        "description": (
            "Sharing and understanding different perceptions of faith, "
            "spirituality, and religious practices."
        ),
        "image_url": "/storage/topics/Religion.png",
    },
    {
        "name": "Politics",
        "description": (
            "Examining varied perceptions of political events, "
            "ideologies, and figures."
        ),
        "image_url": "/storage/topics/politics.jpg",
    },
    {
        "name": "Economy",
        "description": (
            "Understanding how different groups perceive economic trends, "
            "policies, and their personal impact."
        ),
        "image_url": "/storage/topics/economy.png",
    },
    {
        "name": "Society",
        "description": (
            "Discussing varying perceptions of social norms, issues, "
            "and community dynamics."
        ),
        "image_url": "/storage/topics/Society.webp",
    },
    {
        "name": "Lifestyle",
        "description": (
            "Exploring different perceptions of what constitutes a "
            "fulfilling or aspirational lifestyle."
        ),
        "image_url": "/storage/topics/lifestyle.avif",
    },
]

PLANS = [
    {
        "code": "free",
        "name": "Free",
        "description": "Explore Perception and contribute signals.",
        "price_cents": 0,
        "currency": "USD",
        "interval": "month",
        "analytics_enabled": False,
        "max_topics": 0,
        "verification_included": False,
        "trial_days": 0,
    },
    {
        "code": "professional",
        "name": "Professional",
        "description": (
            "Analytics for professionals making evidence-informed " "decisions."
        ),
        "price_cents": 1200,
        "currency": "USD",
        "interval": "month",
        "analytics_enabled": True,
        "max_topics": 5,
        "verification_included": True,
        "trial_days": 14,
    },
    {
        "code": "research",
        "name": "Research",
        "description": (
            "Broader topic coverage for research and cross-field analysis."
        ),
        "price_cents": 2900,
        "currency": "USD",
        "interval": "month",
        "analytics_enabled": True,
        "max_topics": 15,
        "verification_included": True,
        "trial_days": 14,
    },
    {
        "code": "business",
        "name": "Business",
        "description": (
            "High-volume analytics for market and product decision-making."
        ),
        "price_cents": 7900,
        "currency": "USD",
        "interval": "month",
        "analytics_enabled": True,
        "max_topics": 50,
        "verification_included": True,
        "trial_days": 14,
    },
]

MOTIVATIONS = [
    "Every perspective is a piece of the whole picture — share yours.",
    "The view from where you stand is worth more than you think.",
    "Understanding starts with listening to a different vantage point.",
    "One topic, a thousand angles — what's yours today?",
    "Your take might be the missing piece for someone else.",
]
