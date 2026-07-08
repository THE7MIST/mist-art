import csv
import hashlib
import html
import json
import mimetypes
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.database.repository import repository, utcnow
from app.schemas import (
    ArtifactCategorySummary,
    CatalogFileRecord,
    EvidenceCatalog,
    EvidenceGeneralInfo,
    FileStatistics,
    FileTimeline,
    HashSet,
    PartitionInfo,
)


ARCHIVE_EXTENSIONS = {"zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "heic"}
OFFICE_EXTENSIONS = {"doc", "docx", "docm", "xls", "xlsx", "xlsm", "ppt", "pptx", "pptm", "odt", "ods", "odp"}
VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "wmv", "flv", "webm", "m4v"}
AUDIO_EXTENSIONS = {"mp3", "wav", "flac", "aac", "m4a", "ogg", "wma"}
SOURCE_EXTENSIONS = {"py", "js", "ts", "tsx", "jsx", "java", "c", "cpp", "cs", "go", "rs", "php", "rb", "sh"}
SCRIPT_EXTENSIONS = {"ps1", "bat", "cmd", "vbs", "js", "jse", "wsf", "sh"}
EXECUTABLE_EXTENSIONS = {"exe", "dll", "sys", "scr", "msi", "com", "jar", "elf", "app"}
DATABASE_EXTENSIONS = {"sqlite", "sqlite3", "db", "mdb", "accdb", "edb"}
LOG_EXTENSIONS = {"log", "evtx", "etl"}
CONFIG_EXTENSIONS = {"ini", "cfg", "conf", "yaml", "yml", "toml", "properties", "xml", "json"}
CERT_EXTENSIONS = {"cer", "crt", "pem", "pfx", "p12", "key"}
EMAIL_EXTENSIONS = {"pst", "ost", "eml", "msg", "mbox"}
BROWSER_NAMES = {"history", "cookies", "web data", "places.sqlite", "favicons", "login data"}
REGISTRY_NAMES = {"sam", "system", "software", "security", "ntuser.dat", "usrclass.dat", "amcache.hve"}
MEMORY_EXTENSIONS = {"mem", "vmem", "lime", "dmp"}
VM_EXTENSIONS = {"vmdk", "vhd", "vhdx", "qcow2", "vdi", "ova", "ovf"}
TEXT_PREVIEW_EXTENSIONS = SOURCE_EXTENSIONS | SCRIPT_EXTENSIONS | CONFIG_EXTENSIONS | {"txt", "csv", "html", "htm", "md"}
FINANCIAL_TERMS = {"finance", "financial", "bank", "invoice", "salary", "tax", "payment", "wallet", "password"}
SUSPICIOUS_TERMS = {"password", "secret", "keylogger", "payload", "crack", "hack", "dump", "exfil", "malware"}
MAX_MEMBER_HASH_BYTES = 64 * 1024 * 1024


class CatalogEngine:
    def build_catalog(self, case_id: str, selected_timezone: str = "UTC") -> EvidenceCatalog:
        case = repository.get_case(case_id)
        if case is None:
            raise KeyError(case_id)

        evidence_items = repository.list_evidence(case_id)
        if not evidence_items:
            raise ValueError("No evidence is available to catalog")

        warnings: list[str] = []
        records: list[CatalogFileRecord] = []
        folder_count = 0
        primary_hashes = HashSet()
        total_image_size = 0
        primary_filename = evidence_items[0]["filename"]
        primary_format = evidence_items[0]["detected_type"]

        for evidence in evidence_items:
            path = Path(evidence["storage_path"])
            total_image_size += evidence["size_bytes"]
            hashes = self._hash_file(path)
            if evidence == evidence_items[0]:
                primary_hashes = hashes

            records.append(
                self._record_for_path(
                    case_id=case_id,
                    evidence=evidence,
                    filename=evidence["filename"],
                    original_path=f"/{evidence['filename']}",
                    source_kind="uploaded_file",
                    source_ref=f"evidence://{evidence['id']}",
                    size=evidence["size_bytes"],
                    hashes=hashes,
                    timestamp=Path(evidence["storage_path"]).stat().st_mtime,
                    timezone_name=selected_timezone,
                    extra_flags=["evidence_container"],
                )
            )

            if evidence["detected_type"] == "zip":
                member_records, member_folders = self._enumerate_zip(case_id, evidence, selected_timezone)
                records.extend(member_records)
                folder_count += member_folders
            elif evidence["detected_type"] in {"raw-disk-image", "ewf", "virtual-disk"}:
                warnings.append(
                    f"{evidence['filename']} is a disk image. Full filesystem enumeration is staged for the disk plugin "
                    "with Sleuth Kit/pytsk3 support; the MVP catalog includes container metadata until that worker is enabled."
                )
            elif evidence["detected_type"] == "memory-image":
                warnings.append(
                    f"{evidence['filename']} is a memory image. File-level cataloging requires Volatility extraction."
                )

        self._mark_duplicates(records)
        statistics = self._statistics(records, folder_count)
        categories = self._categories(records)
        catalog_id = str(uuid4())
        general_info = EvidenceGeneralInfo(
            case_name=case["name"],
            evidence_filename=primary_filename if len(evidence_items) == 1 else f"{len(evidence_items)} evidence items",
            evidence_format=primary_format if len(evidence_items) == 1 else "mixed",
            image_size=total_image_size,
            hashes=primary_hashes,
            acquisition_tool="Uploaded through MIST Artifact",
            acquisition_timestamp=datetime.fromisoformat(evidence_items[0]["created_at"]),
            verification_status="verified-sha256" if primary_hashes.sha256 else "pending",
            capacity=total_image_size,
            partitions=[
                PartitionInfo(
                    index=0,
                    description="Logical uploaded container",
                    start_sector=0,
                    size_bytes=total_image_size,
                    filesystem="pending external parser" if primary_format in {"raw-disk-image", "ewf", "virtual-disk"} else primary_format,
                )
            ],
        )
        catalog = EvidenceCatalog(
            id=catalog_id,
            case_id=case_id,
            generated_at=utcnow(),
            status="completed",
            timezone=selected_timezone,
            general_info=general_info,
            statistics=statistics,
            categories=categories,
            ai_summary=self._ai_summary(statistics, records),
            report_paths={},
            files_indexed=len(records),
            deleted_files=statistics.deleted_files,
            recovered_files=statistics.recovered_files,
            warnings=warnings,
        )
        report_paths = self._write_reports(catalog, records)
        catalog.report_paths = report_paths
        repository.save_catalog(
            catalog.model_dump(mode="json"),
            [record.model_dump(mode="json") for record in records],
        )
        return catalog

    def _enumerate_zip(
        self,
        case_id: str,
        evidence: dict,
        selected_timezone: str,
    ) -> tuple[list[CatalogFileRecord], int]:
        records: list[CatalogFileRecord] = []
        folder_count = 0
        zip_path = Path(evidence["storage_path"])
        try:
            with zipfile.ZipFile(zip_path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        folder_count += 1
                        continue
                    hashes, header = self._hash_zip_member(archive, member)
                    timestamp = datetime(*member.date_time, tzinfo=timezone.utc).timestamp()
                    records.append(
                        self._record_for_path(
                            case_id=case_id,
                            evidence=evidence,
                            filename=Path(member.filename).name or member.filename,
                            original_path=f"/{evidence['filename']}/{member.filename}",
                            source_kind="orphan" if self._is_orphan_candidate(member.filename) else "zip_member",
                            source_ref=f"zip://{evidence['id']}/{member.filename}",
                            size=member.file_size,
                            hashes=hashes,
                            timestamp=timestamp,
                            timezone_name=selected_timezone,
                            encrypted=bool(member.flag_bits & 0x1),
                            header=header,
                        )
                    )
        except zipfile.BadZipFile:
            return records, folder_count
        return records, folder_count

    def _record_for_path(
        self,
        case_id: str,
        evidence: dict,
        filename: str,
        original_path: str,
        source_kind: str,
        source_ref: str,
        size: int,
        hashes: HashSet,
        timestamp: float,
        timezone_name: str,
        encrypted: bool = False,
        header: bytes | None = None,
        extra_flags: list[str] | None = None,
    ) -> CatalogFileRecord:
        extension = Path(filename).suffix.lower().lstrip(".")
        basename = Path(filename).name
        category = self._category(filename)
        detected_magic = self._magic_name(header or self._read_header(source_ref, evidence))
        signature_mismatch = self._signature_mismatch(extension, category, detected_magic)
        deleted = self._is_deleted_candidate(original_path)
        hidden = basename.startswith(".") or "/." in original_path.replace("\\", "/")
        system = basename.lower() in {"pagefile.sys", "hiberfil.sys"} or "/windows/" in original_path.lower()
        executable = extension in EXECUTABLE_EXTENSIONS or detected_magic == "pe"
        password_protected = encrypted
        flags = list(extra_flags or [])
        if deleted:
            flags.append("deleted")
        if hidden:
            flags.append("hidden")
        if encrypted:
            flags.append("encrypted")
        if password_protected:
            flags.append("password_protected")
        if signature_mismatch:
            flags.append("signature_mismatch")
        if executable:
            flags.append("executable")
        if self._is_ads(original_path):
            flags.append("alternate_data_stream")
        if self._is_large_archive(extension, size):
            flags.append("large_archive")
        if self._has_financial_name(original_path):
            flags.append("financial")
        if self._has_suspicious_name(original_path):
            flags.append("suspicious_name")
        if extension in {"docm", "xlsm", "pptm"}:
            flags.append("office_macro_candidate")
        if self._is_browser_artifact(filename, original_path):
            flags.append("browser_artifact")
        if extension in EMAIL_EXTENSIONS:
            flags.append("email_file")

        score = self._interest_score(flags, category, timestamp)
        timeline_value = datetime.fromtimestamp(timestamp, timezone.utc)
        record = CatalogFileRecord(
            id=str(uuid4()),
            case_id=case_id,
            evidence_id=evidence["id"],
            filename=basename,
            path=original_path,
            original_path=original_path,
            extension=extension,
            category=category,
            size=size,
            source_kind=source_kind,  # type: ignore[arg-type]
            source_ref=source_ref,
            mime_type=mimetypes.guess_type(filename)[0],
            deleted=deleted,
            hidden=hidden,
            system=system,
            encrypted=encrypted,
            password_protected=password_protected,
            signature_mismatch=signature_mismatch,
            executable=executable,
            interesting=score >= 60,
            suspicious="suspicious_name" in flags or score >= 80,
            timeline=FileTimeline(
                created_time=timeline_value,
                modified_time=timeline_value,
                accessed_time=timeline_value,
                changed_time=timeline_value if source_kind == "tsk_record" else None,
                deleted_time=timeline_value if deleted else None,
                timezone=timezone_name,
            ),
            hashes=hashes,
            interest_score=score,
            recovery_status="recoverable" if source_kind in {"zip_member", "orphan", "carved"} else "not_recoverable",
            integrity="intact" if source_kind in {"zip_member", "uploaded_file"} else "unknown",
            confidence=0.95 if source_kind in {"zip_member", "uploaded_file"} else 0.7,
            flags=sorted(set(flags)),
            detected_magic=detected_magic,
            preview_supported=self._preview_supported(category, extension),
        )
        return record

    def _hash_file(self, path: Path) -> HashSet:
        md5_digest = hashlib.md5(usedforsecurity=False)
        sha1_digest = hashlib.sha1()
        sha256_digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                md5_digest.update(chunk)
                sha1_digest.update(chunk)
                sha256_digest.update(chunk)
        return HashSet(md5=md5_digest.hexdigest(), sha1=sha1_digest.hexdigest(), sha256=sha256_digest.hexdigest())

    def _hash_zip_member(self, archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> tuple[HashSet, bytes]:
        md5_digest = hashlib.md5(usedforsecurity=False)
        sha1_digest = hashlib.sha1()
        sha256_digest = hashlib.sha256()
        header = b""
        read_total = 0
        if member.file_size > MAX_MEMBER_HASH_BYTES:
            with archive.open(member) as handle:
                header = handle.read(64)
            return HashSet(), header
        with archive.open(member) as handle:
            while chunk := handle.read(1024 * 1024):
                if not header:
                    header = chunk[:64]
                read_total += len(chunk)
                md5_digest.update(chunk)
                sha1_digest.update(chunk)
                sha256_digest.update(chunk)
        if read_total == 0:
            return HashSet(md5=md5_digest.hexdigest(), sha1=sha1_digest.hexdigest(), sha256=sha256_digest.hexdigest()), header
        return HashSet(md5=md5_digest.hexdigest(), sha1=sha1_digest.hexdigest(), sha256=sha256_digest.hexdigest()), header

    def _read_header(self, source_ref: str, evidence: dict) -> bytes:
        if not source_ref.startswith("evidence://"):
            return b""
        path = Path(evidence["storage_path"])
        with path.open("rb") as handle:
            return handle.read(64)

    def _category(self, filename: str) -> str:
        extension = Path(filename).suffix.lower().lstrip(".")
        lower_name = Path(filename).name.lower()
        if extension in IMAGE_EXTENSIONS:
            return "Images"
        if extension == "pdf":
            return "PDF"
        if extension in OFFICE_EXTENSIONS:
            return "Office Documents"
        if extension in ARCHIVE_EXTENSIONS:
            return "Archives"
        if extension in SOURCE_EXTENSIONS:
            return "Source Code"
        if extension in EXECUTABLE_EXTENSIONS:
            return "Executables"
        if extension in SCRIPT_EXTENSIONS:
            return "Scripts"
        if extension in VIDEO_EXTENSIONS:
            return "Videos"
        if extension in AUDIO_EXTENSIONS:
            return "Audio"
        if extension in DATABASE_EXTENSIONS:
            return "Databases"
        if extension in LOG_EXTENSIONS:
            return "Logs"
        if extension in CONFIG_EXTENSIONS:
            return "Configuration Files"
        if extension in CERT_EXTENSIONS:
            return "Certificates"
        if extension in EMAIL_EXTENSIONS:
            return "Email Files"
        if lower_name in BROWSER_NAMES:
            return "Browser Artifacts"
        if lower_name in REGISTRY_NAMES:
            return "Registry Files"
        if extension in MEMORY_EXTENSIONS or lower_name == "memory.raw":
            return "Memory Dumps"
        if extension in VM_EXTENSIONS:
            return "Virtual Machine Files"
        return "Other"

    def _magic_name(self, header: bytes) -> str | None:
        signatures = [
            (b"PK\x03\x04", "zip"),
            (b"%PDF", "pdf"),
            (b"MZ", "pe"),
            (b"SQLite format 3", "sqlite"),
            (b"\x7fELF", "elf"),
            (b"\x89PNG", "png"),
            (b"\xff\xd8\xff", "jpeg"),
            (b"GIF87a", "gif"),
            (b"GIF89a", "gif"),
            (b"Rar!\x1a\x07", "rar"),
            (b"7z\xbc\xaf\x27\x1c", "7z"),
        ]
        for magic, name in signatures:
            if header.startswith(magic):
                return name
        if len(header) > 12 and header[4:8] == b"ftyp":
            return "mp4"
        return None

    def _signature_mismatch(self, extension: str, category: str, detected_magic: str | None) -> bool:
        if not detected_magic or not extension:
            return False
        expected = {
            "zip": "zip",
            "pdf": "pdf",
            "exe": "pe",
            "dll": "pe",
            "png": "png",
            "jpg": "jpeg",
            "jpeg": "jpeg",
            "gif": "gif",
            "rar": "rar",
            "7z": "7z",
            "sqlite": "sqlite",
            "db": "sqlite",
        }
        if extension in expected:
            return expected[extension] != detected_magic
        return category == "Other" and detected_magic in {"pe", "zip", "pdf", "sqlite"}

    def _is_deleted_candidate(self, path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return any(part in normalized for part in ["/$recycle.bin/", "/deleted/", "/.trash/", "/trash/", "$i", "$r"])

    def _is_orphan_candidate(self, path: str) -> bool:
        normalized = path.replace("\\", "/").lower()
        return "/orphan/" in normalized or normalized.startswith("orphan/")

    def _is_ads(self, path: str) -> bool:
        normalized = path.replace("\\", "/")
        name = normalized.rsplit("/", 1)[-1]
        return ":" in name and not re.match(r"^[a-zA-Z]:", name)

    def _is_large_archive(self, extension: str, size: int) -> bool:
        return extension in ARCHIVE_EXTENSIONS and size >= 100 * 1024 * 1024

    def _has_financial_name(self, path: str) -> bool:
        lower = path.lower()
        return any(term in lower for term in FINANCIAL_TERMS)

    def _has_suspicious_name(self, path: str) -> bool:
        lower = path.lower()
        return any(term in lower for term in SUSPICIOUS_TERMS)

    def _is_browser_artifact(self, filename: str, path: str) -> bool:
        lower_name = filename.lower()
        lower_path = path.lower()
        return lower_name in BROWSER_NAMES or any(part in lower_path for part in ["/chrome/", "/firefox/", "/edge/", "/brave/"])

    def _interest_score(self, flags: list[str], category: str, timestamp: float) -> int:
        score = 0
        weighted_flags = {
            "deleted": 25,
            "encrypted": 25,
            "password_protected": 25,
            "signature_mismatch": 30,
            "executable": 20,
            "large_archive": 20,
            "financial": 20,
            "browser_artifact": 18,
            "email_file": 15,
            "office_macro_candidate": 30,
            "hidden": 10,
            "alternate_data_stream": 25,
            "suspicious_name": 25,
            "duplicate": 12,
        }
        for flag in flags:
            score += weighted_flags.get(flag, 0)
        age_seconds = utcnow().timestamp() - timestamp
        if age_seconds <= 7 * 24 * 60 * 60:
            score += 15
        if category in {"Executables", "Archives", "Email Files", "Browser Artifacts"}:
            score += 10
        return min(score, 100)

    def _preview_supported(self, category: str, extension: str) -> bool:
        return (
            category in {"Images", "PDF", "Office Documents", "Logs", "Configuration Files", "Source Code", "Scripts"}
            or extension in TEXT_PREVIEW_EXTENSIONS
            or category != "Other"
        )

    def _mark_duplicates(self, records: list[CatalogFileRecord]) -> None:
        counts = Counter(record.hashes.sha256 for record in records if record.hashes.sha256)
        for record in records:
            if record.hashes.sha256 and counts[record.hashes.sha256] > 1:
                if "duplicate" not in record.flags:
                    record.flags.append("duplicate")
                record.interest_score = min(record.interest_score + 12, 100)
                record.interesting = record.interest_score >= 60

    def _statistics(self, records: list[CatalogFileRecord], folder_count: int) -> FileStatistics:
        return FileStatistics(
            total_files=len(records),
            total_folders=folder_count,
            deleted_files=sum(1 for item in records if item.deleted),
            recovered_files=sum(1 for item in records if item.recovered),
            hidden_files=sum(1 for item in records if item.hidden),
            system_files=sum(1 for item in records if item.system),
            executable_files=sum(1 for item in records if item.executable),
            office_documents=sum(1 for item in records if item.category == "Office Documents"),
            pdf_documents=sum(1 for item in records if item.category == "PDF"),
            images=sum(1 for item in records if item.category == "Images"),
            videos=sum(1 for item in records if item.category == "Videos"),
            audio_files=sum(1 for item in records if item.category == "Audio"),
            zip_archives=sum(1 for item in records if item.extension == "zip"),
            rar_archives=sum(1 for item in records if item.extension == "rar"),
            seven_zip_archives=sum(1 for item in records if item.extension == "7z"),
            encrypted_files=sum(1 for item in records if item.encrypted),
            password_protected_files=sum(1 for item in records if item.password_protected),
            signature_mismatches=sum(1 for item in records if item.signature_mismatch),
            emails=sum(1 for item in records if item.category == "Email Files"),
            interesting_files=sum(1 for item in records if item.interesting),
            suspicious_files=sum(1 for item in records if item.suspicious),
        )

    def _categories(self, records: list[CatalogFileRecord]) -> list[ArtifactCategorySummary]:
        sizes: dict[str, int] = defaultdict(int)
        counts: dict[str, int] = defaultdict(int)
        for record in records:
            counts[record.category] += 1
            sizes[record.category] += record.size
        category_order = [
            "Images",
            "PDF",
            "Office Documents",
            "Archives",
            "Source Code",
            "Executables",
            "Scripts",
            "Videos",
            "Audio",
            "Databases",
            "Logs",
            "Configuration Files",
            "Certificates",
            "Email Files",
            "Browser Artifacts",
            "Registry Files",
            "Memory Dumps",
            "Virtual Machine Files",
            "Other",
        ]
        return [
            ArtifactCategorySummary(name=name, count=counts[name], total_size=sizes[name], view_filter=name)
            for name in category_order
            if counts[name] > 0
        ]

    def _ai_summary(self, stats: FileStatistics, records: list[CatalogFileRecord]) -> str:
        top = sorted(records, key=lambda item: item.interest_score, reverse=True)[:3]
        top_names = ", ".join(item.filename for item in top) if top else "None"
        lines = [
            "Evidence contains:",
            f"{stats.images} Images",
            f"{stats.pdf_documents} PDFs",
            f"{stats.zip_archives} ZIP Archives",
            f"{stats.deleted_files} Deleted Files",
            f"{stats.password_protected_files} Password Protected Files",
            f"{stats.office_documents} Office Documents",
            f"{stats.executable_files} Executables",
            f"Total Files: {stats.total_files}",
            f"Most Interesting Files: {top_names}",
        ]
        return "\n".join(lines)

    def _write_reports(self, catalog: EvidenceCatalog, records: list[CatalogFileRecord]) -> dict[str, str]:
        settings = get_settings()
        report_dir = settings.report_dir / catalog.case_id / "catalog"
        report_dir.mkdir(parents=True, exist_ok=True)
        base = report_dir / catalog.id
        markdown_path = base.with_suffix(".md")
        json_path = base.with_suffix(".json")
        csv_path = base.with_suffix(".csv")
        html_path = base.with_suffix(".html")

        markdown = self._catalog_markdown(catalog, records)
        markdown_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(
            json.dumps(
                {
                    "catalog": catalog.model_dump(mode="json"),
                    "files": [record.model_dump(mode="json") for record in records],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "filename",
                    "path",
                    "extension",
                    "category",
                    "size",
                    "deleted",
                    "hidden",
                    "encrypted",
                    "recovered",
                    "created",
                    "modified",
                    "accessed",
                    "changed",
                    "deleted_time",
                    "sha256",
                    "interest_score",
                ],
            )
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "filename": record.filename,
                        "path": record.path,
                        "extension": record.extension,
                        "category": record.category,
                        "size": record.size,
                        "deleted": record.deleted,
                        "hidden": record.hidden,
                        "encrypted": record.encrypted,
                        "recovered": record.recovered,
                        "created": record.timeline.created_time,
                        "modified": record.timeline.modified_time,
                        "accessed": record.timeline.accessed_time,
                        "changed": record.timeline.changed_time,
                        "deleted_time": record.timeline.deleted_time,
                        "sha256": record.hashes.sha256,
                        "interest_score": record.interest_score,
                    }
                )
        html_path.write_text(self._catalog_html(catalog, records), encoding="utf-8")
        return {
            "markdown": str(markdown_path),
            "json": str(json_path),
            "csv": str(csv_path),
            "html": str(html_path),
        }

    def _catalog_markdown(self, catalog: EvidenceCatalog, records: list[CatalogFileRecord]) -> str:
        lines = [
            f"# Evidence Catalog - {catalog.general_info.case_name}",
            "",
            f"Generated: {catalog.generated_at.isoformat()}",
            "",
            "## Evidence Summary",
            "",
            f"- Evidence: {catalog.general_info.evidence_filename}",
            f"- Format: {catalog.general_info.evidence_format}",
            f"- Image size: {catalog.general_info.image_size}",
            f"- MD5: {catalog.general_info.hashes.md5}",
            f"- SHA1: {catalog.general_info.hashes.sha1}",
            f"- SHA256: {catalog.general_info.hashes.sha256}",
            f"- Verification: {catalog.general_info.verification_status}",
            "",
            "## AI Summary",
            "",
            catalog.ai_summary,
            "",
            "## File Statistics",
            "",
        ]
        for name, value in catalog.statistics.model_dump().items():
            lines.append(f"- {name.replace('_', ' ').title()}: {value}")
        lines.extend(["", "## Deleted File Report", ""])
        deleted = [record for record in records if record.deleted]
        if deleted:
            for record in deleted:
                lines.append(
                    f"- {record.filename} | {record.original_path} | {record.size} bytes | "
                    f"{record.recovery_status} | confidence {round(record.confidence * 100)}%"
                )
        else:
            lines.append("- No deleted files were identified in the current catalog pass.")
        lines.extend(["", "## Interesting File Report", ""])
        for record in sorted(records, key=lambda item: item.interest_score, reverse=True)[:25]:
            lines.append(f"- {record.filename} | score {record.interest_score} | {', '.join(record.flags) or 'no flags'}")
        return "\n".join(lines)

    def _catalog_html(self, catalog: EvidenceCatalog, records: list[CatalogFileRecord]) -> str:
        rows = "\n".join(
            "<tr>"
            f"<td>{html.escape(record.filename)}</td>"
            f"<td>{html.escape(record.path)}</td>"
            f"<td>{html.escape(record.category)}</td>"
            f"<td>{record.size}</td>"
            f"<td>{record.deleted}</td>"
            f"<td>{record.interest_score}</td>"
            "</tr>"
            for record in records
        )
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>MIST Evidence Catalog</title>"
            "<style>body{font-family:Arial,sans-serif;margin:24px;color:#18181b}"
            "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:6px}"
            "th{background:#eef8f6;text-align:left}</style></head><body>"
            f"<h1>Evidence Catalog - {html.escape(catalog.general_info.case_name)}</h1>"
            f"<pre>{html.escape(catalog.ai_summary)}</pre>"
            "<table><thead><tr><th>Filename</th><th>Path</th><th>Category</th><th>Size</th>"
            "<th>Deleted</th><th>Interest</th></tr></thead><tbody>"
            f"{rows}</tbody></table></body></html>"
        )


catalog_engine = CatalogEngine()
