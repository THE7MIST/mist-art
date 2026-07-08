export interface CaseRead {
  id: string;
  name: string;
  examiner?: string | null;
  description?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  evidence_ids: string[];
  question_ids: string[];
}

export interface EvidenceRead {
  id: string;
  case_id: string;
  filename: string;
  content_type?: string | null;
  size_bytes: number;
  sha256: string;
  storage_path: string;
  detected_type: string;
  readonly: boolean;
  created_at: string;
}

export interface QuestionRead {
  id: string;
  case_id: string;
  text: string;
  intent: string;
  status: string;
  created_at: string;
}

export interface EvidenceItem {
  label: string;
  value: string;
  source: string;
  confidence: number;
}

export interface GuiWorkflow {
  tool: "FTK Imager" | "Autopsy" | "X-Ways" | "Volatility Workbench";
  steps: string[];
  expected_observation: string;
}

export interface VerificationStep {
  method: string;
  command?: string | null;
  expected_output: string;
  notes?: string | null;
}

export interface AnswerResult {
  question_id: string;
  question: string;
  objective: string;
  theory: string;
  answer: string;
  confidence: number;
  required_artifacts: string[];
  selected_plugins: string[];
  procedure: string[];
  gui_workflows: GuiWorkflow[];
  cli_verification: VerificationStep[];
  evidence: EvidenceItem[];
  reasoning: string;
  alternative_verification: string[];
  expected_output: string;
  report_paragraph: string;
}

export interface InvestigationReport {
  id: string;
  case_id: string;
  title: string;
  generated_at: string;
  answers: AnswerResult[];
  markdown_path: string;
  json_path: string;
}

export interface PluginManifest {
  id: string;
  name: string;
  category: string;
  version: string;
  description: string;
  inputs: string[];
  outputs: string[];
  tools: string[];
  enabled: boolean;
}

export interface HashSet {
  md5?: string | null;
  sha1?: string | null;
  sha256?: string | null;
}

export interface PartitionInfo {
  index: number;
  description: string;
  start_sector?: number | null;
  end_sector?: number | null;
  size_bytes?: number | null;
  filesystem?: string | null;
  volume_label?: string | null;
}

export interface EvidenceGeneralInfo {
  case_name: string;
  evidence_filename: string;
  evidence_format: string;
  image_size: number;
  hashes: HashSet;
  acquisition_tool?: string | null;
  acquisition_timestamp?: string | null;
  verification_status: string;
  drive_model?: string | null;
  serial_number?: string | null;
  capacity?: number | null;
  volume_label?: string | null;
  filesystem?: string | null;
  sector_size?: number | null;
  cluster_size?: number | null;
  partitions: PartitionInfo[];
}

export interface FileStatistics {
  total_files: number;
  total_folders: number;
  deleted_files: number;
  recovered_files: number;
  hidden_files: number;
  system_files: number;
  executable_files: number;
  office_documents: number;
  pdf_documents: number;
  images: number;
  videos: number;
  audio_files: number;
  zip_archives: number;
  rar_archives: number;
  seven_zip_archives: number;
  encrypted_files: number;
  password_protected_files: number;
  signature_mismatches: number;
  emails: number;
  urls: number;
  ip_addresses: number;
  interesting_files: number;
  suspicious_files: number;
}

export interface ArtifactCategorySummary {
  name: string;
  count: number;
  total_size: number;
  view_filter: string;
}

export interface FileTimeline {
  created_time?: string | null;
  modified_time?: string | null;
  accessed_time?: string | null;
  changed_time?: string | null;
  deleted_time?: string | null;
  timezone: string;
}

export interface CatalogFileRecord {
  id: string;
  case_id: string;
  evidence_id: string;
  filename: string;
  path: string;
  original_path: string;
  extension: string;
  category: string;
  size: number;
  source_kind: "uploaded_file" | "zip_member" | "tsk_record" | "carved" | "orphan" | "recovered";
  source_ref: string;
  mime_type?: string | null;
  deleted: boolean;
  hidden: boolean;
  system: boolean;
  encrypted: boolean;
  password_protected: boolean;
  recovered: boolean;
  signature_mismatch: boolean;
  executable: boolean;
  interesting: boolean;
  suspicious: boolean;
  timeline: FileTimeline;
  hashes: HashSet;
  owner?: string | null;
  interest_score: number;
  recovery_status: "not_recoverable" | "recoverable" | "recovered" | "failed";
  integrity: "unknown" | "intact" | "partial" | "damaged";
  confidence: number;
  flags: string[];
  detected_magic?: string | null;
  preview_supported: boolean;
}

export interface EvidenceCatalog {
  id: string;
  case_id: string;
  generated_at: string;
  status: "queued" | "indexing" | "completed" | "failed";
  timezone: string;
  general_info: EvidenceGeneralInfo;
  statistics: FileStatistics;
  categories: ArtifactCategorySummary[];
  ai_summary: string;
  report_paths: Record<string, string>;
  files_indexed: number;
  deleted_files: number;
  recovered_files: number;
  warnings: string[];
}

export interface PreviewResponse {
  file_id: string;
  filename: string;
  preview_type: "image" | "pdf" | "text" | "office" | "hex" | "metadata" | "binary" | "unsupported";
  content?: string | null;
  encoding?: string | null;
  hex?: string | null;
  strings: string[];
  metadata: Record<string, unknown>;
  download_path?: string | null;
}

export interface RecoveryRequest {
  file_ids: string[];
  mode: "selected" | "all_deleted" | "all_images" | "all_documents" | "all_archives" | "everything";
}

export interface RecoveredFile {
  file_id: string;
  filename: string;
  original_path: string;
  export_path: string;
  status: "recovered" | "skipped" | "failed";
  sha256?: string | null;
  message?: string | null;
}

export interface RecoveryResult {
  id: string;
  case_id: string;
  requested_file_ids: string[];
  mode: string;
  recovered_count: number;
  skipped_count: number;
  export_root: string;
  files: RecoveredFile[];
  created_at: string;
}
