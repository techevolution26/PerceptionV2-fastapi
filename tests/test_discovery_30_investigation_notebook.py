from pathlib import Path

from app.models.models import InvestigationThread
from app.schemas.investigation_threads import InvestigationThreadCreate, InvestigationThreadUpdate


def test_investigation_notebook_contract_exists():
    assert Path("DISCOVERY_30_INVESTIGATION_NOTEBOOK.md").exists()
    assert InvestigationThread.__tablename__ == "investigation_threads"


def test_investigation_thread_input_is_bounded():
    payload = InvestigationThreadCreate(
        perception_id=1,
        title="Investigate the recurring pattern",
        question="What independent evidence could confirm or challenge this observation?",
        rationale="The question emerged from a qualified discussion pattern.",
        evidence_basis="comment_intelligence",
        validation_step="Check independent sources and additional perspectives.",
        evidence_trace_id="trace-123",
    )
    assert payload.question
    assert InvestigationThreadUpdate(status="in_progress").status == "in_progress"
