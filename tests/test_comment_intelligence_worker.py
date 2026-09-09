from app.services.comment_intelligence_provider import _retry_after_seconds


def test_retry_after_header_is_parsed():
    class Response:
        headers = {"retry-after": "1728"}

    assert _retry_after_seconds(Response()) == 1728


def test_rate_limit_reset_is_fallback():
    class Response:
        headers = {"x-ratelimit-reset-requests": "3600"}

    assert _retry_after_seconds(Response()) == 3600


def test_invalid_retry_headers_return_none():
    class Response:
        headers = {
            "retry-after": "not-a-number",
            "x-ratelimit-reset-requests": "also-invalid",
        }

    assert _retry_after_seconds(Response()) is None
