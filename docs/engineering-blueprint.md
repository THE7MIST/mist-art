# MIST Artifact Engineering Blueprint

## 1. Product Positioning

MIST Artifact is an AI-powered digital forensics investigation and verification platform. Its job is not to replace FTK, Autopsy, Sleuth Kit, Volatility, RegRipper, or YARA. Its job is to orchestrate them into a reproducible investigation workflow.

Every answer should include:

```text
Question
Objective
Theory
Investigation Procedure
GUI Steps
CLI Verification
Evidence Found
Why This Is The Answer
Alternative Verification
Expected Output
Report Paragraph
Export JSON/PDF/Markdown
```

## 2. Runtime Architecture

```text
React Console
  -> FastAPI Gateway
    -> Workflow / AI Planner
    -> Plugin Manager
    -> Evidence Repository
    -> Report Engine
  -> Celery Worker
    -> Sleuth Kit / Volatility / RegRipper / YARA / Plaso
  -> PostgreSQL / MinIO / OpenSearch / Redis
  -> Local LLM through Ollama or vLLM
```

The API should stay responsive. Heavy evidence processing belongs in Celery workers. Evidence mounts must be read-only, and exported derivatives must be stored separately with hashes.

## 3. Evidence Flow

```text
Upload evidence
  -> Create immutable evidence record
  -> Calculate SHA-256
  -> Detect container type
  -> Store read-only path
  -> Queue parser jobs
  -> Convert tool output to structured JSON
  -> Index searchable metadata
  -> Feed structured facts to AI reasoning
```

The AI engine should never receive raw disk images or memory dumps. It receives structured evidence extracted by deterministic tools.

## 4. Question Solver Flow

```text
Question paper
  -> OCR/text extraction
  -> Question segmentation
  -> Intent classification
  -> Artifact requirements
  -> Plugin plan
  -> Tool execution
  -> Cross verification
  -> Confidence score
  -> Report generation
```

Example:

```text
"How many ZIP files?"
  -> zip_count intent
  -> filesystem entries + magic bytes
  -> disk plugin + metadata plugin + hash plugin
  -> FTK/Autopsy/TSK reproduction
```

## 5. Data Model

Core tables for the production PostgreSQL implementation:

- `cases`: case metadata, examiner, status.
- `evidence`: uploaded containers, hashes, storage URIs, acquisition metadata.
- `chain_of_custody_events`: who handled what, when, and why.
- `artifacts`: normalized extracted artifacts with type, source, parser, and confidence.
- `files`: filesystem records with path, inode, size, timestamps, deleted state, hash.
- `timeline_events`: normalized event time, source artifact, confidence, timezone.
- `questions`: original question text, detected intent, required plugins, status.
- `answers`: answer text, confidence, reasoning, selected evidence.
- `verifications`: GUI and CLI verification procedures and expected outputs.
- `reports`: generated report artifacts and export paths.
- `plugins`: plugin metadata, versions, sandbox settings.
- `audit_events`: user/API actions, worker actions, and report generation events.

## 6. Plugin Contract

Each plugin must declare:

- `id`
- `name`
- `category`
- `version`
- `description`
- `inputs`
- `outputs`
- `tools`
- `sandbox`

Future executable plugins should implement:

```python
class Plugin:
    def can_handle(self, evidence, question_plan) -> bool: ...
    def run(self, evidence, question_plan) -> PluginResult: ...
    def verify(self, result) -> list[VerificationStep]: ...
    def report(self, result) -> list[EvidenceItem]: ...
    def confidence(self, result) -> float: ...
```

Plugin output must be JSON serializable and evidence-linked. Never store untraceable AI-only conclusions as evidence.

## 7. AI Orchestration

The production AI engine should be a graph:

```text
Question Ingest
  -> Intent Classifier
  -> Evidence Requirement Planner
  -> Plugin Selector
  -> Execution Dispatcher
  -> Structured Evidence Normalizer
  -> Cross Verification
  -> Reasoning Composer
  -> Confidence Calculator
  -> Report Writer
```

Use LangGraph or a similar state-machine approach so every transition is auditable. Prompt output should be validated by Pydantic schemas before it enters the case record.

## 8. RAG Knowledge Base

Knowledge sources:

- Sleuth Kit documentation.
- Autopsy documentation.
- FTK Imager workflows.
- Volatility 3 documentation.
- RegRipper plugin references.
- NIST and SANS references.
- Internal lab notes.

RAG is for explanation and procedure generation. It is not evidence. Any fact about the case must originate from parsed evidence or verified tool output.

## 9. Confidence Model

Recommended scoring inputs:

- Evidence availability.
- Parser reliability.
- Cross-tool agreement.
- Hash verification.
- Artifact specificity.
- Timestamp consistency.
- AI uncertainty.
- Manual verification state.

Example:

```text
FTK says NTFS
Autopsy says NTFS
fsstat says NTFS
SHA-256 unchanged
=> confidence 100%
```

## 10. Security Model

Rules:

- Mount evidence read-only.
- Never modify original evidence.
- Run plugins in isolated containers.
- Disable network by default for forensic workers.
- Apply CPU, memory, and timeout limits.
- Keep tool versions in report metadata.
- Store every export with SHA-256.
- Record audit events for uploads, analysis, report exports, and settings changes.

## 11. Deployment

Default Docker services:

- `frontend`: React/Vite.
- `backend`: FastAPI.
- `worker`: Celery.
- `redis`: queue broker.
- `postgres`: system of record.
- `minio`: object storage.
- `opensearch`: metadata/content search.
- `ollama`: optional local LLM profile.

Run optional LLM service with:

```bash
docker compose --profile llm up --build
```

## 12. Roadmap

Phase 1 MVP:

- Case management.
- Evidence upload and hashing.
- Question parser.
- Plugin planner.
- Markdown/JSON reports.

Phase 2 Core DFIR:

- TSK execution.
- EWF support through libewf/ewfmount.
- File listing and deleted-file extraction.
- Timeline baseline.
- Hash and chain-of-custody records.

Phase 3 AI Copilot:

- LangGraph workflow.
- RAG references.
- Evidence-grounded answer composer.
- Confidence engine.
- GUI workflow generator.

Phase 4 Advanced Forensics:

- Volatility 3.
- Registry parsers.
- Browser SQLite parsers.
- Password recovery orchestration.
- YARA and IOC extraction.

Phase 5 Enterprise:

- Multi-user RBAC.
- Collaboration.
- Case sharing.
- Plugin SDK.
- Audit dashboards.
- Cloud storage connectors.
- Horizontal worker scaling.
