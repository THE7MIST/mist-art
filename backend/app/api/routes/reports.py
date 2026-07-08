from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from app.database.repository import repository
from app.schemas import InvestigationReport


router = APIRouter()


@router.get("/cases/{case_id}/reports/latest", response_model=InvestigationReport)
def latest_report(case_id: str) -> dict:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    report = repository.latest_report(case_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No report has been generated")
    return report


@router.get("/cases/{case_id}/reports/latest/markdown", response_class=PlainTextResponse)
def latest_report_markdown(case_id: str) -> str:
    report = latest_report(case_id)
    markdown_path = Path(report["markdown_path"])
    if not markdown_path.exists():
        raise HTTPException(status_code=404, detail="Markdown report file is missing")
    return markdown_path.read_text(encoding="utf-8")


@router.get("/cases/{case_id}/reports/latest/download")
def download_latest_report(case_id: str) -> FileResponse:
    report = latest_report(case_id)
    markdown_path = Path(report["markdown_path"])
    if not markdown_path.exists():
        raise HTTPException(status_code=404, detail="Markdown report file is missing")
    return FileResponse(markdown_path, media_type="text/markdown", filename=markdown_path.name)
