"""Provider adapter for per-comment semantic analysis."""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("comment_intelligence")

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral", "mixed", "unclear"]},
        "stance": {"type": "string", "enum": ["supportive", "challenging", "mixed", "unclear"]},
        "themes": {"type": "array", "items": {"type": "string", "maxLength": 80}, "maxItems": 10},
        "is_question": {"type": "boolean"},
        "has_concern": {"type": "boolean"},
        "agreement_signal": {"type": "boolean"},
        "disagreement_signal": {"type": "boolean"},
        "quality_score": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "sentiment", "stance", "themes", "is_question", "has_concern",
        "agreement_signal", "disagreement_signal", "quality_score",
    ],
}

SYSTEM_PROMPT = """You analyze one public discussion comment for aggregate conversation intelligence.
Rules:
- Analyze only the supplied comment and perception context.
- Never infer protected traits, identity, profession, location, age, religion, ethnicity, gender, health, politics, or other sensitive attributes.
- Do not identify the commenter.
- sentiment is the comment's expressed emotional orientation.
- stance is whether the comment supports, challenges, mixes, or is unclear about the main claim in the perception.
- themes are short topical phrases grounded in the comment.
- has_concern means the comment explicitly raises a concern, risk, problem, objection, or worry.
- agreement_signal and disagreement_signal are explicit conversational signals, not guesses.
- If evidence is weak, use unclear and lower quality_score.
- Return only the structured result.
"""


class CommentIntelligenceProviderError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _extract_output_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    chunks: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks).strip()


async def analyze_comment(*, comment_body: str, perception_body: str, topic_name: str | None) -> dict[str, Any]:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise CommentIntelligenceProviderError("provider_not_configured")

    payload = {
        "model": settings.COMMENT_INTELLIGENCE_MODEL,
        "store": False,
        "input": [
            {"role": "developer", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "input_text", "text": (
                f"Perception topic: {(topic_name or 'unspecified').strip()[:200]}\n\n"
                f"Perception: {perception_body.strip()[:6000]}\n\n"
                f"Comment: {comment_body.strip()[:6000]}"
            )}]},
        ],
        "text": {"format": {
            "type": "json_schema",
            "name": "comment_intelligence",
            "strict": True,
            "schema": ANALYSIS_SCHEMA,
        }},
    }

    try:
        async with httpx.AsyncClient(base_url=settings.OPENAI_BASE_URL.rstrip("/"), timeout=30.0) as client:
            response = await client.post(
                "/responses",
                json=payload,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        logger.warning("Comment intelligence provider timed out")
        raise CommentIntelligenceProviderError("provider_timeout") from exc
    except httpx.HTTPStatusError as exc:
        logger.warning("Comment intelligence provider returned HTTP %s", exc.response.status_code)
        raise CommentIntelligenceProviderError("provider_http_error") from exc
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Comment intelligence provider request failed: %s", exc.__class__.__name__)
        raise CommentIntelligenceProviderError("provider_request_error") from exc

    if data.get("status") in {"failed", "cancelled", "incomplete"}:
        raise CommentIntelligenceProviderError("provider_incomplete")

    text = _extract_output_text(data)
    if not text:
        raise CommentIntelligenceProviderError("empty_provider_output")
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CommentIntelligenceProviderError("invalid_provider_json") from exc
    if not isinstance(result, dict):
        raise CommentIntelligenceProviderError("invalid_provider_shape")
    return result
