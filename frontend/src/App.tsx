import { FormEvent, useEffect, useMemo, useState } from "react";
import { Archive, FileQuestion, Fingerprint, Play, RefreshCcw, UploadCloud } from "lucide-react";

import { AnswerPanel } from "./components/AnswerPanel";
import { CatalogDashboard } from "./components/CatalogDashboard";
import { EvidenceExplorer } from "./components/EvidenceExplorer";
import { Pipeline } from "./components/Pipeline";
import { PreviewDrawer } from "./components/PreviewDrawer";
import { StatusPill } from "./components/StatusPill";
import { api } from "./services/api";
import type {
  CaseRead,
  CatalogFileRecord,
  EvidenceCatalog,
  EvidenceRead,
  InvestigationReport,
  PluginManifest,
  PreviewResponse,
  QuestionRead,
  RecoveryResult
} from "./types/mist";

function App() {
  const [cases, setCases] = useState<CaseRead[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [evidence, setEvidence] = useState<EvidenceRead[]>([]);
  const [questions, setQuestions] = useState<QuestionRead[]>([]);
  const [plugins, setPlugins] = useState<PluginManifest[]>([]);
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [catalog, setCatalog] = useState<EvidenceCatalog | null>(null);
  const [catalogFiles, setCatalogFiles] = useState<CatalogFileRecord[]>([]);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [recovery, setRecovery] = useState<RecoveryResult | null>(null);
  const [activeTab, setActiveTab] = useState("Overview");
  const [activeCatalogFilter, setActiveCatalogFilter] = useState("all");
  const [catalogKeyword, setCatalogKeyword] = useState("");
  const [caseName, setCaseName] = useState("Case 001");
  const [examiner, setExaminer] = useState("");
  const [questionText, setQuestionText] = useState("How many ZIP files are present?");
  const [bulkQuestions, setBulkQuestions] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCase = useMemo(
    () => cases.find((item) => item.id === selectedCaseId) ?? cases[0],
    [cases, selectedCaseId]
  );

  const filteredCatalogFiles = useMemo(() => {
    const keyword = catalogKeyword.toLowerCase();
    return catalogFiles.filter((file) => {
      if (activeCatalogFilter === "deleted" && !file.deleted) return false;
      if (activeCatalogFilter === "recovered" && !file.recovered) return false;
      if (activeCatalogFilter === "encrypted" && !file.encrypted) return false;
      if (activeCatalogFilter === "interesting" && !file.interesting) return false;
      if (activeCatalogFilter === "zip" && file.extension !== "zip") return false;
      if (
        !["all", "deleted", "recovered", "encrypted", "interesting", "zip"].includes(activeCatalogFilter) &&
        file.category !== activeCatalogFilter
      ) {
        return false;
      }
      if (!keyword) return true;
      return `${file.filename} ${file.path} ${file.extension} ${file.category} ${file.flags.join(" ")}`
        .toLowerCase()
        .includes(keyword);
    });
  }, [activeCatalogFilter, catalogFiles, catalogKeyword]);

  async function loadCases() {
    const loadedCases = await api.listCases();
    setCases(loadedCases);
    if (!selectedCaseId && loadedCases.length > 0) {
      setSelectedCaseId(loadedCases[0].id);
    }
  }

  async function loadCaseData(caseId: string) {
    const [loadedEvidence, loadedQuestions] = await Promise.all([
      api.listEvidence(caseId),
      api.listQuestions(caseId)
    ]);
    setEvidence(loadedEvidence);
    setQuestions(loadedQuestions);
    try {
      setReport(await api.latestReport(caseId));
    } catch {
      setReport(null);
    }
    try {
      const loadedCatalog = await api.getCatalog(caseId);
      const loadedFiles = await api.listCatalogFiles(caseId);
      setCatalog(loadedCatalog);
      setCatalogFiles(loadedFiles);
    } catch {
      setCatalog(null);
      setCatalogFiles([]);
      setPreview(null);
    }
  }

  useEffect(() => {
    api.listPlugins().then(setPlugins).catch(() => setPlugins([]));
    loadCases().catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (selectedCase?.id) {
      loadCaseData(selectedCase.id).catch((err: Error) => setError(err.message));
    }
  }, [selectedCase?.id]);

  async function runAction(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setBusy(false);
    }
  }

  async function createCase(event: FormEvent) {
    event.preventDefault();
    await runAction(async () => {
      const created = await api.createCase({ name: caseName, examiner, description: "Generated in MIST Artifact" });
      await loadCases();
      setSelectedCaseId(created.id);
    });
  }

  async function uploadEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCase) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("evidence") as File | null;
    if (!file || file.size === 0) return;
    await runAction(async () => {
      await api.uploadEvidence(selectedCase.id, file);
      setCatalog(null);
      setCatalogFiles([]);
      setPreview(null);
      await loadCaseData(selectedCase.id);
      formElement.reset();
    });
  }

  async function addQuestion(event: FormEvent) {
    event.preventDefault();
    if (!selectedCase || !questionText.trim()) return;
    await runAction(async () => {
      await api.addQuestion(selectedCase.id, questionText);
      await loadCaseData(selectedCase.id);
    });
  }

  async function importQuestions(event: FormEvent) {
    event.preventDefault();
    if (!selectedCase || !bulkQuestions.trim()) return;
    await runAction(async () => {
      await api.importQuestionsText(selectedCase.id, bulkQuestions);
      setBulkQuestions("");
      await loadCaseData(selectedCase.id);
    });
  }

  async function analyze() {
    if (!selectedCase) return;
    await runAction(async () => {
      const generated = await api.analyze(selectedCase.id);
      setReport(generated);
      await loadCases();
      await loadCaseData(selectedCase.id);
    });
  }

  async function buildCatalog() {
    if (!selectedCase) return;
    await runAction(async () => {
      const generated = await api.buildCatalog(selectedCase.id);
      const files = await api.listCatalogFiles(selectedCase.id);
      setCatalog(generated);
      setCatalogFiles(files);
    });
  }

  function applyCatalogFilter(filter: string) {
    setActiveCatalogFilter(filter);
    setActiveTab(filter === "deleted" ? "Deleted Files" : filter === "recovered" ? "Recovered Files" : "Evidence Explorer");
  }

  async function searchCatalog() {
    if (!selectedCase || !catalogKeyword.trim()) return;
    await runAction(async () => {
      const results = await api.searchCatalog(selectedCase.id, catalogKeyword, "keyword");
      setCatalogFiles(results);
      setActiveCatalogFilter("all");
      setActiveTab("Evidence Explorer");
    });
  }

  async function previewFile(file: CatalogFileRecord) {
    if (!selectedCase) return;
    await runAction(async () => {
      setPreview(await api.previewFile(selectedCase.id, file.id));
      setActiveTab("Preview");
    });
  }

  async function recoverFile(file: CatalogFileRecord) {
    if (!selectedCase) return;
    await runAction(async () => {
      setRecovery(await api.recoverFiles(selectedCase.id, { mode: "selected", file_ids: [file.id] }));
      await loadCaseData(selectedCase.id);
    });
  }

  async function bulkRecover(mode: "all_deleted" | "all_images" | "all_documents" | "all_archives" | "everything") {
    if (!selectedCase) return;
    await runAction(async () => {
      setRecovery(await api.recoverFiles(selectedCase.id, { mode, file_ids: [] }));
      await loadCaseData(selectedCase.id);
      setActiveTab("Recovered Files");
      setActiveCatalogFilter("recovered");
    });
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">M</div>
          <div>
            <h1>MIST Artifact</h1>
            <p>AI DFIR investigation console</p>
          </div>
        </div>

        <form className="panel" onSubmit={createCase}>
          <h2>Case</h2>
          <label>
            Case name
            <input value={caseName} onChange={(event) => setCaseName(event.target.value)} />
          </label>
          <label>
            Examiner
            <input value={examiner} onChange={(event) => setExaminer(event.target.value)} placeholder="Optional" />
          </label>
          <button disabled={busy || !caseName.trim()} type="submit">
            Create Case
          </button>
        </form>

        <section className="panel case-list">
          <div className="section-heading">
            <h2>Cases</h2>
            <button className="icon-button" onClick={() => runAction(loadCases)} title="Refresh cases" type="button">
              <RefreshCcw size={16} />
            </button>
          </div>
          {cases.length === 0 ? (
            <p className="muted">No cases yet.</p>
          ) : (
            cases.map((item) => (
              <button
                className={item.id === selectedCase?.id ? "case-row active" : "case-row"}
                key={item.id}
                onClick={() => setSelectedCaseId(item.id)}
                type="button"
              >
                <span>{item.name}</span>
                <StatusPill label={item.status} tone={item.status === "analyzed" ? "ready" : "neutral"} />
              </button>
            ))
          )}
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Active investigation</p>
            <h2>{selectedCase?.name ?? "Create a case to begin"}</h2>
          </div>
          <button disabled={busy || !selectedCase || questions.length === 0} onClick={analyze} type="button">
            <Play size={16} />
            Analyze
          </button>
          <button disabled={busy || !selectedCase || evidence.length === 0} onClick={buildCatalog} type="button">
            <Archive size={16} />
            Build Catalog
          </button>
        </header>

        {error && <div className="error-banner">{error}</div>}

        <Pipeline />

        <div className="metrics-grid">
          <div className="metric">
            <Archive size={18} />
            <span>{evidence.length}</span>
            <p>Evidence items</p>
          </div>
          <div className="metric">
            <FileQuestion size={18} />
            <span>{questions.length}</span>
            <p>Questions</p>
          </div>
          <div className="metric">
            <Fingerprint size={18} />
            <span>{plugins.length}</span>
            <p>Plugins</p>
          </div>
        </div>

        <CatalogDashboard catalog={catalog} onFilter={applyCatalogFilter} />

        <section className="panel catalog-workspace">
          <div className="catalog-tabs" role="tablist">
            {[
              "Overview",
              "Artifacts",
              "Deleted Files",
              "Recovered Files",
              "Timeline",
              "Interesting Files",
              "Evidence Explorer",
              "Preview",
              "Reports"
            ].map((tab) => (
              <button
                className={activeTab === tab ? "tab-button active" : "tab-button"}
                key={tab}
                onClick={() => {
                  setActiveTab(tab);
                  if (tab === "Deleted Files") setActiveCatalogFilter("deleted");
                  if (tab === "Recovered Files") setActiveCatalogFilter("recovered");
                  if (tab === "Interesting Files") setActiveCatalogFilter("interesting");
                  if (tab === "Evidence Explorer") setActiveCatalogFilter("all");
                }}
                type="button"
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="filter-row">
            {[
              ["all", "All"],
              ["deleted", "Deleted"],
              ["recovered", "Recovered"],
              ["Images", "Images"],
              ["PDF", "PDF"],
              ["zip", "ZIP"],
              ["Office Documents", "DOCX"],
              ["encrypted", "Encrypted"],
              ["Executables", "Executables"],
              ["interesting", "Interesting"]
            ].map(([filter, label]) => (
              <button
                className={activeCatalogFilter === filter ? "filter-chip active" : "filter-chip"}
                key={filter}
                onClick={() => setActiveCatalogFilter(filter)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>

          <div className="search-row">
            <input
              value={catalogKeyword}
              onChange={(event) => setCatalogKeyword(event.target.value)}
              placeholder="Search filename, keyword, extension, hash, URL, IP, email..."
            />
            <button disabled={!selectedCase || !catalogKeyword.trim() || busy} onClick={searchCatalog} type="button">
              Search
            </button>
            <button disabled={!selectedCase || busy} onClick={() => loadCaseData(selectedCase.id)} type="button">
              Reset
            </button>
          </div>

          <div className="bulk-actions">
            <button disabled={!catalog || busy} onClick={() => bulkRecover("all_deleted")} type="button">
              Recover All Deleted Files
            </button>
            <button disabled={!catalog || busy} onClick={() => bulkRecover("all_images")} type="button">
              Recover All Images
            </button>
            <button disabled={!catalog || busy} onClick={() => bulkRecover("all_documents")} type="button">
              Recover All Documents
            </button>
            <button disabled={!catalog || busy} onClick={() => bulkRecover("all_archives")} type="button">
              Recover All Archives
            </button>
            <button disabled={!catalog || busy} onClick={() => bulkRecover("everything")} type="button">
              Recover Everything
            </button>
          </div>

          {recovery && (
            <div className="recovery-banner">
              Recovered {recovery.recovered_count} file(s), skipped {recovery.skipped_count}. Export root:{" "}
              <code>{recovery.export_root}</code>
            </div>
          )}

          {activeTab === "Overview" && catalog && (
            <div className="overview-grid">
              <section>
                <h3>Partition Information</h3>
                {catalog.general_info.partitions.map((partition) => (
                  <p key={partition.index}>
                    {partition.index}: {partition.description} {partition.filesystem ? `(${partition.filesystem})` : ""}
                  </p>
                ))}
              </section>
              <section>
                <h3>Reports</h3>
                <div className="report-links">
                  {Object.keys(catalog.report_paths).map((format) => (
                    <a
                      href={`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/api/cases/${catalog.case_id}/catalog/reports/${format}`}
                      key={format}
                    >
                      {format.toUpperCase()}
                    </a>
                  ))}
                </div>
              </section>
            </div>
          )}

          {activeTab === "Timeline" && (
            <div className="timeline-list">
              {filteredCatalogFiles
                .slice()
                .sort((a, b) => String(b.timeline.modified_time ?? "").localeCompare(String(a.timeline.modified_time ?? "")))
                .slice(0, 80)
                .map((file) => (
                  <div className="timeline-row" key={file.id}>
                    <span>{file.timeline.modified_time ? new Date(file.timeline.modified_time).toLocaleString() : "n/a"}</span>
                    <strong>{file.filename}</strong>
                    <small>{file.category}</small>
                  </div>
                ))}
            </div>
          )}

          {activeTab === "Preview" ? (
            <PreviewDrawer preview={preview} />
          ) : (
            <EvidenceExplorer files={filteredCatalogFiles} onPreview={previewFile} onRecover={recoverFile} />
          )}
        </section>

        <div className="work-grid">
          <section className="panel">
            <div className="section-heading">
              <h2>Evidence</h2>
              <StatusPill label="read-only workflow" tone="ready" />
            </div>
            <form className="upload-box" onSubmit={uploadEvidence}>
              <UploadCloud size={22} />
              <input disabled={!selectedCase || busy} name="evidence" type="file" />
              <button disabled={!selectedCase || busy} type="submit">
                Upload
              </button>
            </form>
            <div className="table">
              {evidence.map((item) => (
                <div className="table-row" key={item.id}>
                  <span>{item.filename}</span>
                  <span>{item.detected_type}</span>
                  <code>{item.sha256.slice(0, 16)}...</code>
                </div>
              ))}
              {selectedCase && evidence.length === 0 && <p className="muted">Upload Case1.001, E01, raw, memory, ZIP, or supporting artifacts.</p>}
            </div>
          </section>

          <section className="panel">
            <h2>Questions</h2>
            <form className="stacked-form" onSubmit={addQuestion}>
              <label>
                Single question
                <input value={questionText} onChange={(event) => setQuestionText(event.target.value)} />
              </label>
              <button disabled={!selectedCase || busy || !questionText.trim()} type="submit">
                Add Question
              </button>
            </form>
            <form className="stacked-form" onSubmit={importQuestions}>
              <label>
                Question paper text
                <textarea
                  value={bulkQuestions}
                  onChange={(event) => setBulkQuestions(event.target.value)}
                  placeholder={"1. What is the filesystem?\n2. How many ZIP files are present?"}
                />
              </label>
              <button disabled={!selectedCase || busy || !bulkQuestions.trim()} type="submit">
                Import Questions
              </button>
            </form>
            <div className="question-list">
              {questions.map((item) => (
                <div className="question-row" key={item.id}>
                  <p>{item.text}</p>
                  <StatusPill label={item.intent} tone={item.status === "answered" ? "ready" : "neutral"} />
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="panel">
          <div className="section-heading">
            <h2>Generated Investigation</h2>
            {report && <StatusPill label={new Date(report.generated_at).toLocaleString()} tone="working" />}
          </div>
          {!report ? (
            <p className="muted">Run analysis to generate answers, evidence, GUI workflows, CLI verification, confidence, and report paragraphs.</p>
          ) : (
            <div className="answers">
              {report.answers.map((answer) => (
                <AnswerPanel answer={answer} key={answer.question_id} />
              ))}
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

export default App;
