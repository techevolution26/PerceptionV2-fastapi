from collections import Counter
from typing import Any

from app.services.perception_intelligence import MINIMUM_SAMPLE


COMPARISON_LIMIT = 5


def _dist(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key) or "unclear") for row in rows)
    total = sum(counts.values())
    if not total:
        return []
    return [
        {"label": label, "comments": count, "share": round(count / total, 4)}
        for label, count in counts.most_common()
    ]


def _themes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for row in rows:
        for theme in row.get("themes") or []:
            value = str(theme).strip()
            if value:
                counts[value] += 1
    total = sum(counts.values())
    return [
        {"theme": theme, "comments": count, "share": round(count / total, 4)}
        for theme, count in counts.most_common(5)
    ] if total else []


def build_comparative_intelligence(
    datasets: list[dict[str, Any]],
    *,
    minimum: int = MINIMUM_SAMPLE,
    intent: str = "general_exploration",
) -> dict[str, Any]:
    """Compare qualifying perceptions without identifying participants.

    The comparison is descriptive. It never claims that one perception caused
    another result and it does not rank people or expose participant identity.
    """
    qualified: list[dict[str, Any]] = []
    for dataset in datasets:
        rows = dataset.get("rows", [])
        if len(rows) < minimum:
            qualified.append({
                **dataset,
                "status": "insufficient_sample",
                "sample_size": len(rows),
                "leading_stance": None,
                "leading_theme": None,
                "stance_distribution": [],
                "top_themes": [],
            })
            continue
        sentiment = _dist(rows, "sentiment")
        stance = _dist(rows, "stance")
        themes = _themes(rows)
        qualified.append({
            **dataset,
            "status": "available",
            "sample_size": len(rows),
            "sentiment_distribution": sentiment,
            "stance_distribution": stance,
            "top_themes": themes,
            "leading_stance": stance[0]["label"] if stance else None,
            "leading_theme": themes[0]["theme"] if themes else None,
        })

    available = [item for item in qualified if item["status"] == "available"]
    comparisons: list[dict[str, Any]] = []
    for index, left in enumerate(available):
        for right in available[index + 1:]:
            left_stance = left["stance_distribution"][0]["label"] if left["stance_distribution"] else None
            right_stance = right["stance_distribution"][0]["label"] if right["stance_distribution"] else None
            left_themes = {item["theme"] for item in left["top_themes"]}
            right_themes = {item["theme"] for item in right["top_themes"]}
            shared = sorted(left_themes & right_themes)
            stance_changed = bool(left_stance and right_stance and left_stance != right_stance)
            thematic_difference = bool(left_stance == right_stance and not shared)
            comparison_type = "aligned" if left_stance == right_stance and shared else "stance_difference" if stance_changed else "theme_difference" if thematic_difference else "mixed"
            comparisons.append({
                "perception_a_id": left["perception_id"],
                "perception_a_title": left["title"],
                "perception_b_id": right["perception_id"],
                "perception_b_title": right["title"],
                "sample_size_a": left["sample_size"],
                "sample_size_b": right["sample_size"],
                "leading_stance_a": left_stance,
                "leading_stance_b": right_stance,
                "shared_themes": shared,
                "type": comparison_type,
                "description": (
                    "The perceptions show the same leading stance with overlapping themes."
                    if comparison_type == "aligned"
                    else "The perceptions show different leading stances in their qualifying response samples."
                    if comparison_type == "stance_difference"
                    else "The perceptions share a leading stance but their leading themes do not overlap."
                    if comparison_type == "theme_difference"
                    else "The qualifying evidence shows a mixed comparative pattern."
                ),
            })

    strongest = sorted(available, key=lambda item: item["sample_size"], reverse=True)[:3]
    observations = [
        {
            "type": "largest_qualifying_sample",
            "perception_id": item["perception_id"],
            "title": item["title"],
            "sample_size": item["sample_size"],
            "leading_stance": item["stance_distribution"][0]["label"] if item["stance_distribution"] else None,
        }
        for item in strongest
    ]
    status = "available" if len(available) >= 2 else "insufficient_sample"
    return {
        "schema_version": "1.0",
        "intent": intent,
        "status": status,
        "sample_minimum": minimum,
        "perceptions": [
            {key: value for key, value in item.items() if key != "rows"}
            for item in qualified
        ],
        "comparisons": comparisons[:20],
        "observations": observations,
        "limitations": [
            "Comparisons are descriptive and based on analyzed platform responses.",
            "A difference does not establish why perceptions differ or establish causation.",
            "Qualifying platform responses are not automatically representative of a wider population.",
            "Individual participant identities are not exposed.",
        ],
        "decision_note": (
            f"Comparative intelligence is framed for {intent.replace('_', ' ')}. "
            "The underlying observations remain unchanged by the decision lens."
        ),
    }
