CREATE TABLE cases (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  examiner TEXT,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'created',
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE evidence (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  filename TEXT NOT NULL,
  content_type TEXT,
  size_bytes BIGINT NOT NULL,
  md5 TEXT,
  sha1 TEXT,
  sha256 TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  detected_type TEXT NOT NULL,
  readonly BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE evidence_catalogs (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  generated_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  general_info JSONB NOT NULL,
  statistics JSONB NOT NULL,
  categories JSONB NOT NULL,
  ai_summary TEXT NOT NULL,
  report_paths JSONB NOT NULL DEFAULT '{}',
  warnings JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE catalog_files (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  evidence_id TEXT NOT NULL REFERENCES evidence(id),
  filename TEXT NOT NULL,
  path TEXT NOT NULL,
  original_path TEXT NOT NULL,
  extension TEXT,
  category TEXT NOT NULL,
  size BIGINT NOT NULL,
  source_kind TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  mime_type TEXT,
  deleted BOOLEAN NOT NULL DEFAULT FALSE,
  hidden BOOLEAN NOT NULL DEFAULT FALSE,
  system BOOLEAN NOT NULL DEFAULT FALSE,
  encrypted BOOLEAN NOT NULL DEFAULT FALSE,
  password_protected BOOLEAN NOT NULL DEFAULT FALSE,
  recovered BOOLEAN NOT NULL DEFAULT FALSE,
  signature_mismatch BOOLEAN NOT NULL DEFAULT FALSE,
  executable BOOLEAN NOT NULL DEFAULT FALSE,
  interesting BOOLEAN NOT NULL DEFAULT FALSE,
  suspicious BOOLEAN NOT NULL DEFAULT FALSE,
  timeline JSONB NOT NULL,
  hashes JSONB NOT NULL,
  owner TEXT,
  interest_score INTEGER NOT NULL DEFAULT 0,
  recovery_status TEXT NOT NULL DEFAULT 'not_recoverable',
  integrity TEXT NOT NULL DEFAULT 'unknown',
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  flags JSONB NOT NULL DEFAULT '[]',
  detected_magic TEXT,
  preview_supported BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE recovery_actions (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  mode TEXT NOT NULL,
  requested_file_ids JSONB NOT NULL,
  recovered_count INTEGER NOT NULL DEFAULT 0,
  skipped_count INTEGER NOT NULL DEFAULT 0,
  export_root TEXT NOT NULL,
  files JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE audit_events (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES cases(id),
  action TEXT NOT NULL,
  actor TEXT NOT NULL DEFAULT 'system',
  target TEXT,
  details JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_catalog_files_case_category ON catalog_files(case_id, category);
CREATE INDEX idx_catalog_files_case_deleted ON catalog_files(case_id, deleted);
CREATE INDEX idx_catalog_files_case_recovered ON catalog_files(case_id, recovered);
CREATE INDEX idx_catalog_files_case_interest ON catalog_files(case_id, interest_score DESC);
CREATE INDEX idx_catalog_files_hashes ON catalog_files USING GIN (hashes);
CREATE INDEX idx_catalog_files_flags ON catalog_files USING GIN (flags);
CREATE INDEX idx_audit_events_case_time ON audit_events(case_id, created_at DESC);
