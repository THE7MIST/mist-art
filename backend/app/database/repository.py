import json
import shutil
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_state() -> dict:
    return {
        "cases": {},
        "evidence": {},
        "questions": {},
        "reports": {},
        "catalogs": {},
        "catalog_files": {},
        "recovery_actions": {},
        "audit_events": {},
    }


class MistRepository:
    """Small JSON-backed repository for the MVP.

    The production path should replace this with PostgreSQL models while keeping
    the public methods stable for API and worker code.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.state_path = self.settings.cache_dir / "mist_state.json"
        self.lock = RLock()
        self.state = new_state()
        self._load()

    def _load(self) -> None:
        if not self.state_path.exists():
            self._ensure_state_keys()
            return
        with self.state_path.open("r", encoding="utf-8") as handle:
            self.state.update(json.load(handle))
        self._ensure_state_keys()

    def _ensure_state_keys(self) -> None:
        for key, value in new_state().items():
            self.state.setdefault(key, value)

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2, default=str)
        tmp_path.replace(self.state_path)

    def create_case(self, name: str, examiner: str | None, description: str | None) -> dict:
        now = utcnow().isoformat()
        case_id = str(uuid4())
        case = {
            "id": case_id,
            "name": name,
            "examiner": examiner,
            "description": description,
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "evidence_ids": [],
            "question_ids": [],
        }
        with self.lock:
            self.state["cases"][case_id] = case
            self._save()
        return case

    def list_cases(self) -> list[dict]:
        return sorted(self.state["cases"].values(), key=lambda item: item["created_at"], reverse=True)

    def get_case(self, case_id: str) -> dict | None:
        return self.state["cases"].get(case_id)

    async def add_evidence(self, case_id: str, upload: UploadFile) -> dict:
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)

        evidence_id = str(uuid4())
        case_dir = self.settings.upload_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(upload.filename or "evidence.bin").name
        storage_path = case_dir / f"{evidence_id}-{safe_name}"

        digest = sha256()
        size = 0
        with storage_path.open("wb") as handle:
            while chunk := await upload.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                handle.write(chunk)

        detected_type = self.detect_file_type(storage_path, safe_name)
        evidence = {
            "id": evidence_id,
            "case_id": case_id,
            "filename": safe_name,
            "content_type": upload.content_type,
            "size_bytes": size,
            "sha256": digest.hexdigest(),
            "storage_path": str(storage_path),
            "detected_type": detected_type,
            "readonly": True,
            "created_at": utcnow().isoformat(),
        }

        with self.lock:
            self.state["evidence"][evidence_id] = evidence
            case["evidence_ids"].append(evidence_id)
            case["updated_at"] = utcnow().isoformat()
            self.log_audit_event(
                case_id,
                "evidence.uploaded",
                target=evidence_id,
                details={"filename": safe_name, "size_bytes": size, "sha256": evidence["sha256"]},
                save=False,
            )
            self._save()
        return evidence

    def detect_file_type(self, path: Path, filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")
        signatures = {
            b"PK\x03\x04": "zip",
            b"%PDF": "pdf",
            b"MZ": "pe",
            b"SQLite format 3": "sqlite",
            b"EVF": "ewf",
        }
        with path.open("rb") as handle:
            header = handle.read(32)
        for magic, detected in signatures.items():
            if header.startswith(magic):
                return detected
        if suffix in {"e01", "ex01"}:
            return "ewf"
        if suffix in {"dd", "raw", "001", "img"}:
            return "raw-disk-image"
        if suffix in {"vmdk", "vhd", "vhdx", "qcow2", "vdi"}:
            return "virtual-disk"
        if suffix in {"mem", "vmem", "lime"} or filename.lower() == "memory.raw":
            return "memory-image"
        return suffix or "unknown"

    def list_evidence(self, case_id: str) -> list[dict]:
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        return [self.state["evidence"][item_id] for item_id in case["evidence_ids"]]

    def get_evidence(self, evidence_id: str) -> dict | None:
        return self.state["evidence"].get(evidence_id)

    def add_question(self, case_id: str, text: str, intent: str = "unclassified") -> dict:
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        question_id = str(uuid4())
        question = {
            "id": question_id,
            "case_id": case_id,
            "text": text.strip(),
            "intent": intent,
            "status": "queued",
            "created_at": utcnow().isoformat(),
        }
        with self.lock:
            self.state["questions"][question_id] = question
            case["question_ids"].append(question_id)
            case["updated_at"] = utcnow().isoformat()
            self._save()
        return question

    def update_question(self, question_id: str, **updates: str) -> dict:
        with self.lock:
            question = self.state["questions"][question_id]
            question.update(updates)
            self._save()
        return question

    def list_questions(self, case_id: str) -> list[dict]:
        case = self.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        return [self.state["questions"][item_id] for item_id in case["question_ids"]]

    def get_questions(self, case_id: str, question_ids: list[str] | None = None) -> list[dict]:
        questions = self.list_questions(case_id)
        if not question_ids:
            return questions
        wanted = set(question_ids)
        return [question for question in questions if question["id"] in wanted]

    def save_report(self, report: dict) -> dict:
        with self.lock:
            self.state["reports"][report["id"]] = report
            case = self.state["cases"][report["case_id"]]
            case["status"] = "analyzed"
            case["updated_at"] = utcnow().isoformat()
            self._save()
        return report

    def latest_report(self, case_id: str) -> dict | None:
        reports = [item for item in self.state["reports"].values() if item["case_id"] == case_id]
        if not reports:
            return None
        return sorted(reports, key=lambda item: item["generated_at"], reverse=True)[0]

    def save_catalog(self, catalog: dict, files: list[dict]) -> dict:
        case_id = catalog["case_id"]
        with self.lock:
            old_file_ids = [
                file_id
                for file_id, file_record in self.state["catalog_files"].items()
                if file_record["case_id"] == case_id
            ]
            for file_id in old_file_ids:
                del self.state["catalog_files"][file_id]
            self.state["catalogs"][case_id] = catalog
            for file_record in files:
                self.state["catalog_files"][file_record["id"]] = file_record
            case = self.state["cases"][case_id]
            case["status"] = "cataloged"
            case["catalog_id"] = catalog["id"]
            case["updated_at"] = utcnow().isoformat()
            self.log_audit_event(
                case_id,
                "catalog.generated",
                target=catalog["id"],
                details={"files_indexed": catalog.get("files_indexed", 0)},
                save=False,
            )
            self._save()
        return catalog

    def get_catalog(self, case_id: str) -> dict | None:
        return self.state["catalogs"].get(case_id)

    def list_catalog_files(self, case_id: str) -> list[dict]:
        return [
            item
            for item in self.state["catalog_files"].values()
            if item["case_id"] == case_id
        ]

    def get_catalog_file(self, file_id: str) -> dict | None:
        return self.state["catalog_files"].get(file_id)

    def update_catalog_file(self, file_id: str, **updates: object) -> dict:
        with self.lock:
            file_record = self.state["catalog_files"][file_id]
            file_record.update(updates)
            self._refresh_catalog_recovery_counts(file_record["case_id"])
            self._save()
        return file_record

    def _refresh_catalog_recovery_counts(self, case_id: str) -> None:
        catalog = self.state["catalogs"].get(case_id)
        if catalog is None:
            return
        files = self.list_catalog_files(case_id)
        recovered_count = sum(1 for item in files if item.get("recovered"))
        catalog["recovered_files"] = recovered_count
        catalog["statistics"]["recovered_files"] = recovered_count

    def save_recovery_action(self, action: dict) -> dict:
        with self.lock:
            self.state["recovery_actions"][action["id"]] = action
            self.log_audit_event(
                action["case_id"],
                "recovery.completed",
                target=action["id"],
                details={
                    "mode": action["mode"],
                    "recovered_count": action["recovered_count"],
                    "skipped_count": action["skipped_count"],
                },
                save=False,
            )
            self._save()
        return action

    def list_recovery_actions(self, case_id: str) -> list[dict]:
        actions = [
            item
            for item in self.state["recovery_actions"].values()
            if item["case_id"] == case_id
        ]
        return sorted(actions, key=lambda item: item["created_at"], reverse=True)

    def log_audit_event(
        self,
        case_id: str,
        action: str,
        actor: str = "system",
        target: str | None = None,
        details: dict | None = None,
        save: bool = True,
    ) -> dict:
        event_id = str(uuid4())
        event = {
            "id": event_id,
            "case_id": case_id,
            "action": action,
            "actor": actor,
            "target": target,
            "details": details or {},
            "created_at": utcnow().isoformat(),
        }
        self.state["audit_events"][event_id] = event
        if save:
            self._save()
        return event

    def list_audit_events(self, case_id: str) -> list[dict]:
        events = [
            item
            for item in self.state["audit_events"].values()
            if item["case_id"] == case_id
        ]
        return sorted(events, key=lambda item: item["created_at"], reverse=True)

    def reset(self) -> None:
        with self.lock:
            self.state = new_state()
            if self.state_path.exists():
                self.state_path.unlink()
            for directory in (self.settings.upload_dir, self.settings.report_dir):
                if directory.exists():
                    for child in directory.iterdir():
                        if child.name == ".gitkeep":
                            continue
                        if child.is_dir():
                            shutil.rmtree(child)
                        else:
                            child.unlink()


repository = MistRepository()
