from fastapi import APIRouter, File, HTTPException, UploadFile

from app.database.repository import repository
from app.schemas import EvidenceRead


router = APIRouter()


@router.post("/cases/{case_id}/evidence", response_model=EvidenceRead)
async def upload_evidence(case_id: str, file: UploadFile = File(...)) -> dict:
    try:
        return await repository.add_evidence(case_id, file)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc


@router.get("/cases/{case_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(case_id: str) -> list[dict]:
    try:
        return repository.list_evidence(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found") from exc
