"""Deterministic privacy invariants for the production acceptance gate.

This module is intentionally provider- and database-independent. It protects the
API contract from accidentally exposing account credentials, billing identifiers,
private analytical-profile fields, or participant identity through public response
schemas or the external AI payload.
"""

from __future__ import annotations

from typing import Any

MINIMUM_AGGREGATE_SAMPLE = 5

PUBLIC_USER_FORBIDDEN_FIELDS = {
    "email",
    "role",
    "professional_focus",
    "country_code",
    "region",
    "city",
    "analytics_specialties",
    "primary_analytics_topic_id",
    "billing_customer_id",
    "google_sub",
    "token_version",
    "password_hash",
    "is_active",
}

AI_IDENTITY_FORBIDDEN_MARKERS = {
    "user_id",
    "commenter_id",
    "participant_id",
    "name",
    "email",
    "profession",
    "country",
    "country_code",
    "region",
    "city",
    "age",
    "gender",
    "religion",
    "ethnicity",
    "health",
    "politics",
}


def validate_public_schema_fields(fields: set[str]) -> list[str]:
    return sorted(fields & PUBLIC_USER_FORBIDDEN_FIELDS)


def validate_ai_input_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(
        marker for marker in AI_IDENTITY_FORBIDDEN_MARKERS if marker in lowered
    )


def validate_aggregate_sample(
    sample_size: int, minimum: int = MINIMUM_AGGREGATE_SAMPLE
) -> bool:
    return sample_size >= minimum


def validate_observer_measurements(measurements: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in ("views", "shares", "engagement_rate"):
        measurement = measurements.get(name, {})
        if (
            measurement.get("available") is not False
            or measurement.get("value") is not None
        ):
            errors.append(f"observer measurement {name} must be unavailable")
    if measurements.get("daily_activity") not in ([], None):
        errors.append("observer daily_activity must be empty")
    return errors


def intelligence_participation_allowed(user: object) -> bool:
    preferences = getattr(user, "privacy_preferences", None) or {}
    return preferences.get("intelligence_participation", True) is True


def creator_discoverability_allowed(user: object) -> bool:
    preferences = getattr(user, "privacy_preferences", None) or {}
    return preferences.get("creator_discoverability", True) is True
