from fastapi import APIRouter, File, HTTPException, UploadFile

from app.database.repository import repository
from app.engines.question_planner import question_planner
from app.schemas import QuestionCreate, QuestionImportRequest, QuestionRead
from app.services.question_extractor import extract_questions_from_text, extract_questions_from_upload


router = APIRouter()


@router.post("/cases/{case_id}/questions", response_model=QuestionRead)
def add_question(case_id: str, payload: QuestionCreate) -> dict:
    try:
        plan = question_planner.plan(payload.text)
        return repository.add_question(case_id, payload.text, plan.intent)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc


@router.get("/cases/{case_id}/questions", response_model=list[QuestionRead])
def list_questions(case_id: str) -> list[dict]:
    try:
        return repository.list_questions(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc


@router.post("/cases/{case_id}/questions/import/text", response_model=list[QuestionRead])
def import_questions_from_text(case_id: str, payload: QuestionImportRequest) -> list[dict]:
    questions = extract_questions_from_text(payload.text)
    if not questions:
        raise HTTPException(status_code=400, detail="No questions were detected in the supplied text")
    created: list[dict] = []
    try:
        for question in questions:
            plan = question_planner.plan(question)
            created.append(repository.add_question(case_id, question, plan.intent))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
    return created


@router.post("/cases/{case_id}/questions/import/file", response_model=list[QuestionRead])
async def import_questions_from_file(case_id: str, file: UploadFile = File(...)) -> list[dict]:
    questions = await extract_questions_from_upload(file)
    if not questions:
        raise HTTPException(status_code=400, detail="No questions were detected in the uploaded file")
    created: list[dict] = []
    try:
        for question in questions:
            plan = question_planner.plan(question)
            created.append(repository.add_question(case_id, question, plan.intent))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
    return created
