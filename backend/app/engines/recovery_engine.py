import hashlib
import re
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.database.repository import repository, utcnow
from app.schemas import RecoveredFile, RecoveryRequest, RecoveryResult
from app.services.source_resolver import SourceResolutionError, source_resolver


class RecoveryEngine:
    def recover(self, case_id: str, request: RecoveryRequest) -> RecoveryResult:
        selected = self._select_files(case_id, request)
        settings = get_settings()
        export_root = settings.report_dir / case_id / "Recovered"
        export_root.mkdir(parents=True, exist_ok=True)

        recovered: list[RecoveredFile] = []
        for file_record in selected:
            result = self._recover_one(case_id, file_record, export_root)
            recovered.append(result)

        action = RecoveryResult(
            id=str(uuid4()),
            case_id=case_id,
            requested_file_ids=[item["id"] for item in selected],
            mode=request.mode,
            recovered_count=sum(1 for item in recovered if item.status == "recovered"),
            skipped_count=sum(1 for item in recovered if item.status != "recovered"),
            export_root=str(export_root),
            files=recovered,
            created_at=utcnow(),
        )
        repository.save_recovery_action(action.model_dump(mode="json"))
        return action

    def _select_files(self, case_id: str, request: RecoveryRequest) -> list[dict]:
        files = repository.list_catalog_files(case_id)
        if request.mode == "selected":
            wanted = set(request.file_ids)
            return [item for item in files if item["id"] in wanted]
        if request.mode == "all_deleted":
            return [item for item in files if item["deleted"]]
        if request.mode == "all_images":
            return [item for item in files if item["category"] == "Images"]
        if request.mode == "all_documents":
            return [item for item in files if item["category"] in {"PDF", "Office Documents"}]
        if request.mode == "all_archives":
            return [item for item in files if item["category"] == "Archives"]
        return [item for item in files if "evidence_container" not in item.get("flags", [])]

    def _recover_one(self, case_id: str, file_record: dict, export_root: Path) -> RecoveredFile:
        if "evidence_container" in file_record.get("flags", []):
            return self._skipped(file_record, "Original evidence containers are not copied during recovery.")
        if file_record["recovery_status"] == "not_recoverable" and not file_record["source_ref"].startswith(("zip://", "evidence://")):
            return self._skipped(file_record, "File is not recoverable with the currently available source reference.")

        destination = self._destination(export_root, file_record)
        try:
            self._assert_within(export_root, destination)
            source_resolver.copy_to(file_record["source_ref"], destination)
            digest = self._sha256(destination)
            repository.update_catalog_file(
                file_record["id"],
                recovered=True,
                recovery_status="recovered",
                source_kind=file_record["source_kind"],
            )
            repository.log_audit_event(
                case_id,
                "file.recovered",
                target=file_record["id"],
                details={"export_path": str(destination), "sha256": digest},
            )
            return RecoveredFile(
                file_id=file_record["id"],
                filename=file_record["filename"],
                original_path=file_record["original_path"],
                export_path=str(destination),
                status="recovered",
                sha256=digest,
            )
        except (OSError, SourceResolutionError, ValueError) as exc:
            repository.update_catalog_file(file_record["id"], recovery_status="failed")
            return RecoveredFile(
                file_id=file_record["id"],
                filename=file_record["filename"],
                original_path=file_record["original_path"],
                export_path=str(destination),
                status="failed",
                message=str(exc),
            )

    def _destination(self, export_root: Path, file_record: dict) -> Path:
        category_dir = self._category_dir(file_record)
        safe_parts = [self._safe_part(part) for part in Path(file_record["original_path"].strip("/")).parts]
        safe_name = safe_parts[-1] if safe_parts else self._safe_part(file_record["filename"])
        stem = Path(safe_name).stem or "file"
        suffix = Path(safe_name).suffix
        destination = export_root / category_dir / safe_name
        counter = 1
        while destination.exists():
            destination = export_root / category_dir / f"{stem}-{counter}{suffix}"
            counter += 1
        return destination

    def _category_dir(self, file_record: dict) -> str:
        if file_record["source_kind"] == "carved":
            return "Carved"
        if file_record["source_kind"] == "orphan":
            return "Orphan"
        if file_record["deleted"]:
            return "Deleted"
        if file_record["category"] == "Images":
            return "Images"
        if file_record["category"] == "PDF":
            return "PDF"
        if file_record["category"] == "Office Documents":
            return "Office"
        if file_record["category"] == "Archives":
            return "Archives"
        return "Recovered"

    def _safe_part(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", value).strip(" .")
        return cleaned or "file"

    def _assert_within(self, root: Path, destination: Path) -> None:
        root_resolved = root.resolve()
        destination_resolved = destination.resolve()
        destination_resolved.relative_to(root_resolved)

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def _skipped(self, file_record: dict, message: str) -> RecoveredFile:
        return RecoveredFile(
            file_id=file_record["id"],
            filename=file_record["filename"],
            original_path=file_record["original_path"],
            export_path="",
            status="skipped",
            message=message,
        )


recovery_engine = RecoveryEngine()
