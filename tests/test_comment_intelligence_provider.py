from types import SimpleNamespace

import pytest

from app.services.comment_intelligence_provider import (
    ANALYSIS_SCHEMA,
    CommentIntelligenceProviderError,
    _extract_output_text,
    validate_analysis_result,
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


def _valid_result():
    return {
        "sentiment": "neutral",
        "stance": "unclear",
        "themes": ["training"],
        "is_question": False,
        "has_concern": False,
        "agreement_signal": False,
        "disagreement_signal": False,
        "quality_score": 0.8,
    }


def test_validate_analysis_result_accepts_strict_shape():
    result = validate_analysis_result(_valid_result())
    assert result["quality_score"] == 0.8
    assert result["themes"] == ["training"]


def test_validate_analysis_result_rejects_extra_fields():
    result = _valid_result()
    result["extra"] = "nope"
    with pytest.raises(CommentIntelligenceProviderError) as exc:  # noqa: PT011
        validate_analysis_result(result)
    assert exc.value.code == "invalid_provider_schema"


def test_validate_analysis_result_rejects_invalid_quality():
    result = _valid_result()
    result["quality_score"] = 2
    with pytest.raises(CommentIntelligenceProviderError) as exc:  # noqa: PT011
        validate_analysis_result(result)
    assert exc.value.code == "invalid_provider_schema"
