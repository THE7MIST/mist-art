from fastapi import APIRouter, HTTPException

from app.database.repository import repository
from app.engines.catalog_engine import catalog_engine
from app.engines.investigation_engine import investigation_engine
from app.engines.report_engine import report_engine
from app.schemas import AnalysisRequest, InvestigationReport


router = APIRouter()


@router.post("/cases/{case_id}/analyze", response_model=InvestigationReport)
def analyze_case(case_id: str, payload: AnalysisRequest) -> InvestigationReport:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    questions = repository.get_questions(case_id, payload.question_ids)
    if not questions:
        raise HTTPException(status_code=400, detail="No questions are available to analyze")
    if repository.list_evidence(case_id):
        catalog_engine.build_catalog(case_id)
    answers = investigation_engine.analyze_case(
        case_id=case_id,
        question_ids=payload.question_ids,
        learning_mode=payload.learning_mode,
        include_gui_steps=payload.include_gui_steps,
        include_cli_verification=payload.include_cli_verification,
    )
    return report_engine.create_report(case_id, answers)
