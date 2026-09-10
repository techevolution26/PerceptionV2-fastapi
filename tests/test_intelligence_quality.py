from datetime import datetime, timezone

from app.services.intelligence_quality import LOW_QUALITY_THRESHOLD


def test_low_quality_threshold_is_conservative() -> None:
    assert LOW_QUALITY_THRESHOLD == 0.60


def test_quality_service_contract_is_sample_gated() -> None:
    # The service contract uses five analyzed comments as the minimum public
    # semantic sample; this test documents that boundary without a DB/provider.
    from app.services.intelligence_quality import MINIMUM_SAMPLE

    assert MINIMUM_SAMPLE == 5
