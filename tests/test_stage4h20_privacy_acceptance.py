from __future__ import annotations

from app.core.config import Settings
from app.schemas.user import UserMe, UserProfile, UserPublic, UserSlim
from app.services.comment_intelligence_provider import build_analysis_input
from app.services.privacy_contract_guard import (
    MINIMUM_AGGREGATE_SAMPLE,
    validate_aggregate_sample,
    validate_ai_input_text,
    validate_observer_measurements,
    validate_public_schema_fields,
)


def test_public_user_schemas_do_not_expose_account_or_analytics_fields():
    public_models = (UserPublic, UserProfile, UserSlim)
    for model in public_models:
        leaked = validate_public_schema_fields(set(model.model_fields))
        assert leaked == [], f"{model.__name__} exposes private fields: {leaked}"


def test_authenticated_user_schema_is_not_used_as_public_identity_contract():
    assert "email" in UserMe.model_fields
    assert "country_code" in UserMe.model_fields
    assert "analytics_specialties" in UserMe.model_fields
    assert "billing_customer_id" not in UserMe.model_fields
    assert "password_hash" not in UserMe.model_fields


def test_external_ai_payload_contains_only_minimal_discussion_context():
    payload = build_analysis_input(
        comment_body="I think the proposal could work.",
        perception_body="Should this approach be adopted?",
        topic_name="Technology",
    )
    user_text = ""
    for item in payload:
        if item.get("role") == "user":
            content = item.get("content") or []
            user_text = "\n".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict)
            )
    assert validate_ai_input_text(user_text) == []
    assert "i think the proposal could work" in user_text.lower()
    assert "should this approach be adopted" in user_text.lower()
    assert "technology" in user_text.lower()


def test_aggregate_analysis_is_withheld_below_minimum():
    assert MINIMUM_AGGREGATE_SAMPLE == 5
    assert validate_aggregate_sample(4) is False
    assert validate_aggregate_sample(5) is True


def test_observer_cannot_receive_creator_only_metrics():
    errors = validate_observer_measurements(
        {
            "views": {"available": False, "value": None},
            "shares": {"available": False, "value": None},
            "engagement_rate": {"available": False, "value": None},
            "daily_activity": [],
        }
    )
    assert errors == []


def test_production_requires_explicit_external_ai_processing_consent():
    Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="x" * 64,
        CORS_ORIGINS="https://app.example.com",
        SMTP_HOST="smtp.example.com",
        MAIL_FROM="no-reply@example.com",
        PASSWORD_RESET_URL="https://app.example.com/reset-password",
        PUBLIC_APP_URL="https://api.example.com",
        STRIPE_SUCCESS_URL="https://app.example.com/billing/success",
        STRIPE_CANCEL_URL="https://app.example.com/billing/cancel",
        OPENAI_BASE_URL="https://api.openai.com/v1",
        COMMENT_INTELLIGENCE_ENABLED=False,
        COMMENT_INTELLIGENCE_EXTERNAL_PROCESSING_ALLOWED=False,
    )

    try:
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 64,
            CORS_ORIGINS="https://app.example.com",
            SMTP_HOST="smtp.example.com",
            MAIL_FROM="no-reply@example.com",
            PASSWORD_RESET_URL="https://app.example.com/reset-password",
            PUBLIC_APP_URL="https://api.example.com",
            STRIPE_SUCCESS_URL="https://app.example.com/billing/success",
            STRIPE_CANCEL_URL="https://app.example.com/billing/cancel",
            OPENAI_BASE_URL="https://api.openai.com/v1",
            OPENAI_API_KEY="test-key",
            COMMENT_INTELLIGENCE_ENABLED=True,
            COMMENT_INTELLIGENCE_EXTERNAL_PROCESSING_ALLOWED=False,
        )
    except ValueError as exc:
        assert "External comment-intelligence processing" in str(exc)
    else:
        raise AssertionError("Production must not enable external AI processing implicitly")
