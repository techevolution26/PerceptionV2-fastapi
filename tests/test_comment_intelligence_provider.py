from types import SimpleNamespace

import pytest

from app.services.comment_intelligence_provider import (
    ANALYSIS_SCHEMA,
    CommentIntelligenceProviderError,
    _extract_output_text,
)


def test_analysis_schema_is_strict_and_closed():
    assert ANALYSIS_SCHEMA["type"] == "object"
    assert ANALYSIS_SCHEMA["additionalProperties"] is False
    assert set(ANALYSIS_SCHEMA["required"]) == set(ANALYSIS_SCHEMA["properties"])


def test_extract_responses_api_output_text():
    payload = {"output_text": '{"sentiment":"neutral"}'}
    assert _extract_output_text(payload) == '{"sentiment":"neutral"}'


def test_extract_nested_responses_output():
    payload = {
        "output": [
            {"content": [{"type": "output_text", "text": '{"sentiment":"positive"}'}]}
        ]
    }
    assert _extract_output_text(payload) == '{"sentiment":"positive"}'


def test_provider_error_has_safe_code():
    error = CommentIntelligenceProviderError("provider_timeout")
    assert error.code == "provider_timeout"
    assert str(error) == "provider_timeout"
