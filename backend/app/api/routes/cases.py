from fastapi import APIRouter, HTTPException

from app.database.repository import repository
from app.schemas import CaseCreate, CaseRead


router = APIRouter()


@router.post("/cases", response_model=CaseRead)
def create_case(payload: CaseCreate) -> dict:
    return repository.create_case(payload.name, payload.examiner, payload.description)


@router.get("/cases", response_model=list[CaseRead])
def list_cases() -> list[dict]:
    return repository.list_cases()


@router.get("/cases/{case_id}", response_model=CaseRead)
def get_case(case_id: str) -> dict:
    case = repository.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
