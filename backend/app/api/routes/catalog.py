import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.database.repository import repository
from app.engines.catalog_engine import catalog_engine
from app.engines.preview_engine import preview_engine
from app.engines.recovery_engine import recovery_engine
from app.schemas import (
    AuditEvent,
    CatalogFileRecord,
    EvidenceCatalog,
    PreviewResponse,
    RecoveryRequest,
    RecoveryResult,
    SearchRequest,
)
from app.services.source_resolver import source_resolver


router = APIRouter()


@router.post("/cases/{case_id}/catalog/build", response_model=EvidenceCatalog)
def build_catalog(case_id: str, selected_timezone: str = Query("UTC", alias="timezone")) -> EvidenceCatalog:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        return catalog_engine.build_catalog(case_id, selected_timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/cases/{case_id}/catalog", response_model=EvidenceCatalog)
def get_catalog(case_id: str) -> dict:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    catalog = repository.get_catalog(case_id)
    if catalog is None:
        raise HTTPException(status_code=404, detail="Catalog has not been generated")
    return catalog


@router.get("/cases/{case_id}/catalog/files", response_model=list[CatalogFileRecord])
def list_catalog_files(
    case_id: str,
    deleted: bool | None = None,
    recovered: bool | None = None,
    category: str | None = None,
    extension: str | None = None,
    keyword: str | None = None,
    hash: str | None = None,
    owner: str | None = None,
    encrypted: bool | None = None,
    hidden: bool | None = None,
    executable: bool | None = None,
    interesting: bool | None = None,
    large_files: bool | None = None,
    recent_days: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    files = repository.list_catalog_files(case_id)
    return [
        item
        for item in files
        if _matches_filters(
            item,
            deleted=deleted,
            recovered=recovered,
            category=category,
            extension=extension,
            keyword=keyword,
            hash_value=hash,
            owner=owner,
            encrypted=encrypted,
            hidden=hidden,
            executable=executable,
            interesting=interesting,
            large_files=large_files,
            recent_days=recent_days,
            date_from=date_from,
            date_to=date_to,
        )
    ]


@router.get("/cases/{case_id}/catalog/deleted", response_model=list[CatalogFileRecord])
def deleted_files(case_id: str) -> list[dict]:
    return list_catalog_files(case_id, deleted=True)


@router.get("/cases/{case_id}/catalog/interesting", response_model=list[CatalogFileRecord])
def interesting_files(case_id: str) -> list[dict]:
    return sorted(list_catalog_files(case_id, interesting=True), key=lambda item: item["interest_score"], reverse=True)


@router.post("/cases/{case_id}/catalog/search", response_model=list[CatalogFileRecord])
def search_catalog(case_id: str, payload: SearchRequest) -> list[dict]:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    files = repository.list_catalog_files(case_id)
    return [item for item in files if _matches_search(item, payload)]


@router.get("/cases/{case_id}/catalog/files/{file_id}/preview", response_model=PreviewResponse)
def preview_file(case_id: str, file_id: str) -> PreviewResponse:
    file_record = repository.get_catalog_file(file_id)
    if file_record is None or file_record["case_id"] != case_id:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        return preview_engine.preview(file_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc


@router.get("/cases/{case_id}/catalog/files/{file_id}/download")
def download_file(case_id: str, file_id: str) -> StreamingResponse:
    file_record = repository.get_catalog_file(file_id)
    if file_record is None or file_record["case_id"] != case_id:
        raise HTTPException(status_code=404, detail="File not found")

    def stream() -> Iterator[bytes]:
        with source_resolver.open(file_record["source_ref"]) as handle:
            while chunk := handle.read(1024 * 1024):
                yield chunk

    return StreamingResponse(
        stream(),
        media_type=file_record.get("mime_type") or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={file_record['filename']}"},
    )


@router.post("/cases/{case_id}/catalog/recover", response_model=RecoveryResult)
def recover_files(case_id: str, payload: RecoveryRequest) -> RecoveryResult:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if repository.get_catalog(case_id) is None:
        raise HTTPException(status_code=400, detail="Generate the catalog before recovery")
    return recovery_engine.recover(case_id, payload)


@router.get("/cases/{case_id}/catalog/recovery-actions", response_model=list[RecoveryResult])
def recovery_actions(case_id: str) -> list[dict]:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return repository.list_recovery_actions(case_id)


@router.get("/cases/{case_id}/catalog/audit", response_model=list[AuditEvent])
def audit_events(case_id: str) -> list[dict]:
    if repository.get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return repository.list_audit_events(case_id)


@router.get("/cases/{case_id}/catalog/reports/{report_format}")
def catalog_report(case_id: str, report_format: str) -> FileResponse:
    catalog = repository.get_catalog(case_id)
    if catalog is None:
        raise HTTPException(status_code=404, detail="Catalog has not been generated")
    path_value = catalog.get("report_paths", {}).get(report_format)
    if path_value is None:
        raise HTTPException(status_code=404, detail="Report format not available")
    path = Path(path_value)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file is missing")
    media_types = {
        "markdown": "text/markdown",
        "json": "application/json",
        "csv": "text/csv",
        "html": "text/html",
    }
    return FileResponse(path, media_type=media_types.get(report_format, "application/octet-stream"), filename=path.name)


def _matches_filters(item: dict, **filters: object) -> bool:
    for field in ["deleted", "recovered", "encrypted", "hidden", "executable", "interesting"]:
        expected = filters.get(field)
        if expected is not None and item.get(field) is not expected:
            return False
    category = filters.get("category")
    if category and item.get("category") != category:
        return False
    extension = filters.get("extension")
    if extension and item.get("extension", "").lower() != str(extension).lower().lstrip("."):
        return False
    keyword = filters.get("keyword")
    if keyword:
        text = f"{item.get('filename', '')} {item.get('path', '')} {' '.join(item.get('flags', []))}".lower()
        if str(keyword).lower() not in text:
            return False
    hash_value = filters.get("hash_value")
    if hash_value:
        hashes = item.get("hashes", {})
        if str(hash_value).lower() not in {str(value).lower() for value in hashes.values() if value}:
            return False
    owner = filters.get("owner")
    if owner and str(owner).lower() not in str(item.get("owner") or "").lower():
        return False
    if filters.get("large_files") and item.get("size", 0) < 100 * 1024 * 1024:
        return False
    recent_days = filters.get("recent_days")
    if recent_days is not None:
        modified = _parse_time(item.get("timeline", {}).get("modified_time"))
        if modified is None or modified < datetime.now(timezone.utc) - timedelta(days=int(recent_days)):
            return False
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        modified = _parse_time(item.get("timeline", {}).get("modified_time"))
        if modified is None:
            return False
        if date_from and modified < date_from:
            return False
        if date_to and modified > date_to:
            return False
    return True


def _matches_search(item: dict, payload: SearchRequest) -> bool:
    query = payload.query
    lower_query = query.lower()
    path_text = f"{item.get('filename', '')} {item.get('path', '')} {item.get('extension', '')}".lower()
    searchable_text = path_text
    hashes = item.get("hashes", {})
    if payload.mode == "filename":
        return lower_query in item.get("filename", "").lower()
    if payload.mode == "extension":
        return item.get("extension", "").lower() == lower_query.lstrip(".")
    if payload.mode == "hash":
        return lower_query in {str(value).lower() for value in hashes.values() if value}
    if payload.mode == "magic_bytes":
        return lower_query in str(item.get("detected_magic") or "").lower()
    if payload.mode in {"keyword", "regex", "custom_regex", "email", "phone", "credit_card", "ip", "url", "bitcoin"}:
        searchable_text = f"{path_text} {_sample_text(item)}"
    if payload.mode in {"regex", "custom_regex"}:
        return re.search(query, searchable_text, re.IGNORECASE) is not None
    if payload.mode == "email":
        return re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", searchable_text) is not None
    if payload.mode == "phone":
        return re.search(r"\+?\d[\d .()/-]{7,}\d", searchable_text) is not None
    if payload.mode == "credit_card":
        return re.search(r"\b(?:\d[ -]*?){13,19}\b", searchable_text) is not None
    if payload.mode == "ip":
        return re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", searchable_text) is not None
    if payload.mode == "url":
        return re.search(r"https?://|www\.", searchable_text) is not None
    if payload.mode == "bitcoin":
        return re.search(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,59}\b", searchable_text) is not None
    return lower_query in searchable_text


def _sample_text(item: dict) -> str:
    try:
        sample = source_resolver.read_sample(item["source_ref"], 1024 * 1024)
    except Exception:
        return ""
    return sample.decode("utf-8", errors="ignore").lower()


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
