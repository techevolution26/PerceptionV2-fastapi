"""Runtime invariants for the Perception Intelligence contract.

This guard is deliberately deterministic and provider-independent. It does not
change analytical evidence; it catches impossible combinations before the
response is serialized.
"""
from __future__ import annotations

from typing import Any

MINIMUM_SAMPLE = 5


def validate_perception_intelligence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    context = payload.get("context", {})
    semantic = payload.get("semantic", {})
    audience = payload.get("audience", {})
    decision = payload.get("decision_context", {})
    measurements = payload.get("measurements", {})

    scope = context.get("scope")
    if scope not in {"creator_analytics", "conversation_intelligence"}:
        errors.append("context.scope is invalid")

    viewer_lens = context.get("viewer_lens")
    if viewer_lens not in {"author", "observer"}:
        errors.append("context.viewer_lens is invalid")

    if scope == "conversation_intelligence":
        for name in ("views", "shares", "engagement_rate"):
            measurement = measurements.get(name, {})
            if measurement.get("available") is not False or measurement.get("value") is not None:
                errors.append(f"observer measurement {name} must be unavailable")
        if measurements.get("daily_activity") not in ([], None):
            errors.append("observer daily_activity must be empty")

    sample_minimum = int(semantic.get("sample_minimum", MINIMUM_SAMPLE))
    analyzed_count = int(semantic.get("analyzed_comment_count", 0))
    status = semantic.get("status")
    if analyzed_count < 0:
        errors.append("semantic.analyzed_comment_count cannot be negative")
    if status == "available" and analyzed_count < sample_minimum:
        errors.append("semantic.available requires the minimum analyzed-comment sample")
    if status == "insufficient_sample":
        for key in ("sentiment_distribution", "stance_distribution", "top_themes", "concern_themes", "agreement_themes", "disagreement_themes"):
            if semantic.get(key):
                errors.append(f"semantic.{key} must be empty when semantic evidence is insufficient")

    for distribution_key in ("sentiment_distribution", "stance_distribution"):
        for item in semantic.get(distribution_key, []):
            count = int(item.get("comments", -1))
            share = float(item.get("share", -1))
            if count < 0:
                errors.append(f"semantic.{distribution_key} contains a negative comment count")
            if share < 0 or share > 1:
                errors.append(f"semantic.{distribution_key} contains an invalid share")

    unique_participants = int(audience.get("unique_participants", 0))
    breakdown = audience.get("breakdown", {})
    breakdown_available = bool(breakdown.get("available"))
    if unique_participants < 0:
        errors.append("audience.unique_participants cannot be negative")
    if breakdown_available and unique_participants < int(breakdown.get("minimum", MINIMUM_SAMPLE)):
        errors.append("audience breakdown cannot be available below its minimum")
    if not breakdown_available:
        for key in ("countries", "regions", "professional_roles", "verified_professional_roles"):
            if breakdown.get(key):
                errors.append(f"audience.breakdown.{key} must be empty when unavailable")

    if decision.get("evidence_invariant") is not True:
        errors.append("decision_context.evidence_invariant must remain true")

    return errors
