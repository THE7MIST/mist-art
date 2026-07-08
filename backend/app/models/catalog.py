from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CaseModel(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    examiner: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    evidence: Mapped[list["EvidenceModel"]] = relationship(back_populates="case")


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    md5: Mapped[str | None] = mapped_column(String(32))
    sha1: Mapped[str | None] = mapped_column(String(40))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    detected_type: Mapped[str] = mapped_column(String(64), nullable=False)
    readonly: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    case: Mapped[CaseModel] = relationship(back_populates="evidence")


class EvidenceCatalogModel(Base):
    __tablename__ = "evidence_catalogs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    general_info: Mapped[dict] = mapped_column(JSON, nullable=False)
    statistics: Mapped[dict] = mapped_column(JSON, nullable=False)
    categories: Mapped[list] = mapped_column(JSON, nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    report_paths: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, default=list)


class CatalogFileModel(Base):
    __tablename__ = "catalog_files"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512), index=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    extension: Mapped[str] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), index=True)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(160))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    system: Mapped[bool] = mapped_column(Boolean, default=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    password_protected: Mapped[bool] = mapped_column(Boolean, default=False)
    recovered: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    signature_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)
    executable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    interesting: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    suspicious: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    timeline: Mapped[dict] = mapped_column(JSON, nullable=False)
    hashes: Mapped[dict] = mapped_column(JSON, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(256))
    interest_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    recovery_status: Mapped[str] = mapped_column(String(32), default="not_recoverable")
    integrity: Mapped[str] = mapped_column(String(32), default="unknown")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    detected_magic: Mapped[str | None] = mapped_column(String(64))
    preview_supported: Mapped[bool] = mapped_column(Boolean, default=False)


class RecoveryActionModel(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_file_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    recovered_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    export_root: Mapped[str] = mapped_column(Text, nullable=False)
    files: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str] = mapped_column(String(160), default="system")
    target: Mapped[str | None] = mapped_column(String(160))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
