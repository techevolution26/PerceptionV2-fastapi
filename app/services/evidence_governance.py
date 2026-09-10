"""Evidence eligibility and governance for Perception Intelligence."""
from __future__ import annotations
MINIMUM_SAMPLE=5
LOW_QUALITY_THRESHOLD=0.60

def assess_evidence_governance(*, analyzed_count:int,pending_count:int,failed_count:int,quality_status:str,quality_score:float|None,freshness_status:str,minimum:int=MINIMUM_SAMPLE)->dict:
    sample_ok=analyzed_count>=minimum
    quality_ok=quality_status=="available" and (quality_score is None or quality_score>=LOW_QUALITY_THRESHOLD)
    freshness_ok=freshness_status=="current"
    reasons=[]
    if not sample_ok: reasons.append(f"At least {minimum} analyzed comments are required.")
    if quality_status!="available": reasons.append("Analysis quality is not yet available for the minimum sample.")
    elif quality_score is not None and quality_score<LOW_QUALITY_THRESHOLD: reasons.append("Average analysis quality is below the governance threshold.")
    if freshness_status!="current": reasons.append("Stored intelligence does not fully reflect the current conversation.")
    if pending_count: reasons.append(f"{pending_count} comments remain pending analysis.")
    if failed_count: reasons.append(f"{failed_count} comments have failed analysis and are excluded from evidence.")
    status="eligible" if sample_ok and quality_ok and freshness_ok else ("provisional" if sample_ok and quality_ok else "restricted")
    return {"status":status,"minimum_sample":minimum,"analyzed_comment_count":analyzed_count,"pending_comment_count":pending_count,"failed_comment_count":failed_count,"quality_threshold":LOW_QUALITY_THRESHOLD,"quality_score":quality_score if quality_ok else None,"freshness_status":freshness_status,"patterns_eligible":sample_ok and quality_ok,"signals_eligible":sample_ok and quality_ok and freshness_ok,"reasons":reasons,"rules":["Pending comments are not evidence until successfully analyzed.","Failed analyses are excluded from evidence-backed interpretation.","Below-minimum samples cannot qualify patterns or signals.","Low average analysis quality restricts evidence-backed interpretation.","Stale intelligence cannot qualify decision signals until recalculated."]}
