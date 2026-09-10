from datetime import datetime, timezone
from types import SimpleNamespace
from app.services.semantic_model_governance import assess_semantic_model_governance

def r(v,s,st,t,i): return SimpleNamespace(model_version=v,sentiment=s,stance=st,themes=t,analyzed_at=datetime(2026,1,1,0,i,tzinfo=timezone.utc),created_at=datetime(2026,1,1,0,i,tzinfo=timezone.utc))

def test_single_version_stable(): assert assess_semantic_model_governance([r("v1","positive","supportive",["cost"],i) for i in range(5)])["status"]=="stable"

def test_small_comparison_withheld(): assert assess_semantic_model_governance([r("v1","positive","supportive",["cost"],i) for i in range(5)]+[r("v2","negative","challenging",["risk"],i+10) for i in range(4)])["status"]=="insufficient_sample"

def test_large_shift_review(): assert assess_semantic_model_governance([r("v1","positive","supportive",["cost"],i) for i in range(5)]+[r("v2","negative","challenging",["risk"],i+10) for i in range(5)])["status"]=="review_required"
