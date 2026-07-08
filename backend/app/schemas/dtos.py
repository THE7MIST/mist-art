from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    examiner: str | None = None
    description: str | None = None


class CaseRead(BaseModel):
    id: str
    name: str
    examiner: str | None = None
    description: str | None = None
    status: str = "created"
    created_at: datetime
    updated_at: datetime
    evidence_ids: list[str] = []
    question_ids: list[str] = []


class EvidenceRead(BaseModel):
    id: str
    case_id: str
    filename: str
    content_type: str | None = None
    size_bytes: int
    sha256: str
    storage_path: str
    detected_type: str
    readonly: bool = True
    created_at: datetime


class QuestionCreate(BaseModel):
    text: str = Field(..., min_length=3)


class QuestionImportRequest(BaseModel):
    text: str = Field(..., min_length=3)


class QuestionRead(BaseModel):
    id: str
    case_id: str
    text: str
    intent: str = "unclassified"
    status: str = "queued"
    created_at: datetime


class AnalysisRequest(BaseModel):
    question_ids: list[str] | None = None
    learning_mode: bool = True
    include_gui_steps: bool = True
    include_cli_verification: bool = True


class EvidenceItem(BaseModel):
    label: str
    value: str
    source: str
    confidence: float = Field(ge=0, le=1)


class GuiWorkflow(BaseModel):
    tool: Literal["FTK Imager", "Autopsy", "X-Ways", "Volatility Workbench"]
    steps: list[str]
    expected_observation: str


class VerificationStep(BaseModel):
    method: str
    command: str | None = None
    expected_output: str
    notes: str | None = None


class AnswerResult(BaseModel):
    question_id: str
    question: str
    objective: str
    theory: str
    answer: str
    confidence: float = Field(ge=0, le=1)
    required_artifacts: list[str]
    selected_plugins: list[str]
    procedure: list[str]
    gui_workflows: list[GuiWorkflow]
    cli_verification: list[VerificationStep]
    evidence: list[EvidenceItem]
    reasoning: str
    alternative_verification: list[str]
    expected_output: str
    report_paragraph: str
    raw: dict[str, Any] = {}


class InvestigationReport(BaseModel):
    id: str
    case_id: str
    title: str
    generated_at: datetime
    answers: list[AnswerResult]
    markdown_path: str
    json_path: str


class PluginManifest(BaseModel):
    id: str
    name: str
    category: str
    version: str
    description: str
    inputs: list[str]
    outputs: list[str]
    tools: list[str]
    enabled: bool = True
    sandbox: dict[str, Any] = {}


class HashSet(BaseModel):
    md5: str | None = None
    sha1: str | None = None
    sha256: str | None = None


class PartitionInfo(BaseModel):
    index: int
    description: str
    start_sector: int | None = None
    end_sector: int | None = None
    size_bytes: int | None = None
    filesystem: str | None = None
    volume_label: str | None = None


class EvidenceGeneralInfo(BaseModel):
    case_name: str
    evidence_filename: str
    evidence_format: str
    image_size: int
    hashes: HashSet
    acquisition_tool: str | None = None
    acquisition_timestamp: datetime | None = None
    verification_status: str = "verified"
    drive_model: str | None = None
    serial_number: str | None = None
    capacity: int | None = None
    volume_label: str | None = None
    filesystem: str | None = None
    sector_size: int | None = None
    cluster_size: int | None = None
    partitions: list[PartitionInfo] = []


class FileStatistics(BaseModel):
    total_files: int = 0
    total_folders: int = 0
    deleted_files: int = 0
    recovered_files: int = 0
    hidden_files: int = 0
    system_files: int = 0
    executable_files: int = 0
    office_documents: int = 0
    pdf_documents: int = 0
    images: int = 0
    videos: int = 0
    audio_files: int = 0
    zip_archives: int = 0
    rar_archives: int = 0
    seven_zip_archives: int = 0
    encrypted_files: int = 0
    password_protected_files: int = 0
    signature_mismatches: int = 0
    emails: int = 0
    urls: int = 0
    ip_addresses: int = 0
    interesting_files: int = 0
    suspicious_files: int = 0


class ArtifactCategorySummary(BaseModel):
    name: str
    count: int
    total_size: int
    view_filter: str


class FileTimeline(BaseModel):
    created_time: datetime | None = None
    modified_time: datetime | None = None
    accessed_time: datetime | None = None
    changed_time: datetime | None = None
    deleted_time: datetime | None = None
    timezone: str = "UTC"


class CatalogFileRecord(BaseModel):
    id: str
    case_id: str
    evidence_id: str
    filename: str
    path: str
    original_path: str
    extension: str
    category: str
    size: int
    source_kind: Literal["uploaded_file", "zip_member", "tsk_record", "carved", "orphan", "recovered"]
    source_ref: str
    mime_type: str | None = None
    deleted: bool = False
    hidden: bool = False
    system: bool = False
    encrypted: bool = False
    password_protected: bool = False
    recovered: bool = False
    signature_mismatch: bool = False
    executable: bool = False
    interesting: bool = False
    suspicious: bool = False
    timeline: FileTimeline
    hashes: HashSet = HashSet()
    owner: str | None = None
    interest_score: int = Field(default=0, ge=0, le=100)
    recovery_status: Literal["not_recoverable", "recoverable", "recovered", "failed"] = "not_recoverable"
    integrity: Literal["unknown", "intact", "partial", "damaged"] = "unknown"
    confidence: float = Field(default=0.5, ge=0, le=1)
    flags: list[str] = []
    detected_magic: str | None = None
    preview_supported: bool = False


class EvidenceCatalog(BaseModel):
    id: str
    case_id: str
    generated_at: datetime
    status: Literal["queued", "indexing", "completed", "failed"] = "completed"
    timezone: str = "UTC"
    general_info: EvidenceGeneralInfo
    statistics: FileStatistics
    categories: list[ArtifactCategorySummary]
    ai_summary: str
    report_paths: dict[str, str] = {}
    files_indexed: int = 0
    deleted_files: int = 0
    recovered_files: int = 0
    warnings: list[str] = []


class CatalogQuery(BaseModel):
    deleted: bool | None = None
    recovered: bool | None = None
    category: str | None = None
    extension: str | None = None
    keyword: str | None = None
    hash: str | None = None
    owner: str | None = None
    encrypted: bool | None = None
    hidden: bool | None = None
    executable: bool | None = None
    interesting: bool | None = None
    large_files: bool | None = None
    recent_days: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    mode: Literal[
        "filename",
        "extension",
        "regex",
        "keyword",
        "magic_bytes",
        "hash",
        "email",
        "phone",
        "credit_card",
        "ip",
        "url",
        "bitcoin",
        "custom_regex",
    ] = "keyword"


class PreviewResponse(BaseModel):
    file_id: str
    filename: str
    preview_type: Literal["image", "pdf", "text", "office", "hex", "metadata", "binary", "unsupported"]
    content: str | None = None
    encoding: str | None = None
    hex: str | None = None
    strings: list[str] = []
    metadata: dict[str, Any] = {}
    download_path: str | None = None


class RecoveryRequest(BaseModel):
    file_ids: list[str] = []
    mode: Literal[
        "selected",
        "all_deleted",
        "all_images",
        "all_documents",
        "all_archives",
        "everything",
    ] = "selected"


class RecoveredFile(BaseModel):
    file_id: str
    filename: str
    original_path: str
    export_path: str
    status: Literal["recovered", "skipped", "failed"]
    sha256: str | None = None
    message: str | None = None


class RecoveryResult(BaseModel):
    id: str
    case_id: str
    requested_file_ids: list[str]
    mode: str
    recovered_count: int
    skipped_count: int
    export_root: str
    files: list[RecoveredFile]
    created_at: datetime


class AuditEvent(BaseModel):
    id: str
    case_id: str
    action: str
    actor: str = "system"
    target: str | None = None
    details: dict[str, Any] = {}
    created_at: datetime
