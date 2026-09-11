from pydantic import ValidationError
import pytest

from app.core.config import Settings


def _production_kwargs() -> dict:
    return {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "SECRET_KEY": "x" * 64,
        "CORS_ORIGINS": "https://app.example.com",
        "SMTP_HOST": "smtp.example.com",
        "MAIL_FROM": "no-reply@example.com",
        "PASSWORD_RESET_URL": "https://app.example.com/reset-password",
        "PUBLIC_APP_URL": "https://api.example.com",
        "STRIPE_SUCCESS_URL": "https://app.example.com/billing/success",
        "STRIPE_CANCEL_URL": "https://app.example.com/billing/cancel",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
    }


def test_production_rejects_external_ai_without_explicit_permission():
    with pytest.raises(ValueError, match="External comment-intelligence processing"):
        Settings(
            **_production_kwargs(),
            OPENAI_API_KEY="test-key",
            COMMENT_INTELLIGENCE_ENABLED=True,
            COMMENT_INTELLIGENCE_EXTERNAL_PROCESSING_ALLOWED=False,
        )


def test_production_accepts_external_ai_only_when_explicitly_allowed():
    settings = Settings(
        **_production_kwargs(),
        OPENAI_API_KEY="test-key",
        COMMENT_INTELLIGENCE_ENABLED=True,
        COMMENT_INTELLIGENCE_EXTERNAL_PROCESSING_ALLOWED=True,
    )
    assert settings.COMMENT_INTELLIGENCE_ENABLED is True
    assert settings.COMMENT_INTELLIGENCE_EXTERNAL_PROCESSING_ALLOWED is True
