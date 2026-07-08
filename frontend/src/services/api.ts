import type {
  CaseRead,
  CatalogFileRecord,
  EvidenceCatalog,
  EvidenceRead,
  InvestigationReport,
  PluginManifest,
  PreviewResponse,
  QuestionRead,
  RecoveryRequest,
  RecoveryResult
} from "../types/mist";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_PREFIX = `${API_BASE_URL}/api`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listCases: () => request<CaseRead[]>("/cases"),
  createCase: (payload: { name: string; examiner?: string; description?: string }) =>
    request<CaseRead>("/cases", { method: "POST", body: JSON.stringify(payload) }),
  listEvidence: (caseId: string) => request<EvidenceRead[]>(`/cases/${caseId}/evidence`),
  uploadEvidence: (caseId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<EvidenceRead>(`/cases/${caseId}/evidence`, { method: "POST", body: form });
  },
  listQuestions: (caseId: string) => request<QuestionRead[]>(`/cases/${caseId}/questions`),
  addQuestion: (caseId: string, text: string) =>
    request<QuestionRead>(`/cases/${caseId}/questions`, {
      method: "POST",
      body: JSON.stringify({ text })
    }),
  importQuestionsText: (caseId: string, text: string) =>
    request<QuestionRead[]>(`/cases/${caseId}/questions/import/text`, {
      method: "POST",
      body: JSON.stringify({ text })
    }),
  analyze: (caseId: string) =>
    request<InvestigationReport>(`/cases/${caseId}/analyze`, {
      method: "POST",
      body: JSON.stringify({
        learning_mode: true,
        include_gui_steps: true,
        include_cli_verification: true
      })
    }),
  latestReport: (caseId: string) => request<InvestigationReport>(`/cases/${caseId}/reports/latest`),
  listPlugins: () => request<PluginManifest[]>("/plugins"),
  buildCatalog: (caseId: string, timezone = "UTC") =>
    request<EvidenceCatalog>(`/cases/${caseId}/catalog/build?timezone=${encodeURIComponent(timezone)}`, {
      method: "POST"
    }),
  getCatalog: (caseId: string) => request<EvidenceCatalog>(`/cases/${caseId}/catalog`),
  listCatalogFiles: (caseId: string, query = "") =>
    request<CatalogFileRecord[]>(`/cases/${caseId}/catalog/files${query}`),
  searchCatalog: (caseId: string, query: string, mode = "keyword") =>
    request<CatalogFileRecord[]>(`/cases/${caseId}/catalog/search`, {
      method: "POST",
      body: JSON.stringify({ query, mode })
    }),
  previewFile: (caseId: string, fileId: string) =>
    request<PreviewResponse>(`/cases/${caseId}/catalog/files/${fileId}/preview`),
  recoverFiles: (caseId: string, payload: RecoveryRequest) =>
    request<RecoveryResult>(`/cases/${caseId}/catalog/recover`, {
      method: "POST",
      body: JSON.stringify(payload)
    })
};
