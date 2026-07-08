# MIST Artifact

**MIST Artifact** is an AI-native digital forensics investigation and verification platform scaffold. It is designed to turn investigation questions into structured forensic workflows:

```text
Question -> Objective -> Theory -> Procedure -> GUI Steps -> CLI Verification
         -> Evidence -> Reasoning -> Expected Output -> Report
```

This repository contains a runnable MVP foundation:

- React + Vite investigation console.
- FastAPI gateway with case, evidence, question, analysis, report, and plugin APIs.
- Celery worker skeleton for heavy forensic jobs.
- Plugin manifests for disk, memory, registry, browser, timeline, report, hash, metadata, and password modules.
- Docker Compose stack for API, frontend, worker, Redis, PostgreSQL, MinIO, OpenSearch, and optional Ollama.
- Report generation in Markdown and JSON.
- Honest mock-safe analyzers that hash uploaded evidence, classify file signatures, plan forensic plugins, and generate reproducible FTK/Autopsy/TSK workflows.

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- MinIO console: http://localhost:9001
- OpenSearch: http://localhost:9200

## Local Backend Development

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Local Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Current Capability

The MVP scaffold can:

- Create cases.
- Upload evidence and calculate SHA-256.
- Detect basic file signatures such as ZIP/PDF/Windows executables.
- Add or import investigation questions.
- Classify questions into forensic intents.
- Select relevant plugins.
- Generate answers with evidence, confidence, GUI reproduction steps, CLI commands, and report paragraphs.
- Export latest analysis as Markdown/JSON.

Real forensic execution is intentionally isolated behind plugins. The default configuration does not modify evidence and does not execute external forensic binaries unless `ENABLE_EXTERNAL_TOOLS=true`.

## Roadmap

See [docs/engineering-blueprint.md](docs/engineering-blueprint.md) for the full architecture, data model, plugin SDK, AI orchestration plan, security model, and phased build roadmap.
