from app.services.evidence_governance import assess_evidence_governance

def test_restricts_below_minimum():
    r=assess_evidence_governance(analyzed_count=4,pending_count=0,failed_count=0,quality_status="not_ready",quality_score=None,freshness_status="current")
    assert r["status"]=="restricted" and not r["patterns_eligible"] and not r["signals_eligible"]

def test_pending_is_provisional():
    r=assess_evidence_governance(analyzed_count=6,pending_count=1,failed_count=0,quality_status="available",quality_score=0.8,freshness_status="pending")
    assert r["status"]=="provisional" and r["patterns_eligible"] and not r["signals_eligible"]
