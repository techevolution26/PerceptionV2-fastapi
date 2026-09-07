import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token


def test_access_token_contains_and_validates_security_claims(monkeypatch):
    token = create_access_token(42, token_version=3, scope="admin")
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["scope"] == "admin"
    assert payload["ver"] == 3
    assert payload["iss"] == "perception-api"
    assert payload["aud"] == "perception-client"


def test_production_rejects_debug_and_weak_secret():
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="short",
            RATE_LIMIT_FAIL_OPEN=False,
            CORS_ORIGINS="https://example.com",
        )
