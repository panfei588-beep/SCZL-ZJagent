# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CorpClaw** — AI-powered digital employee for aerospace rocket quality anomaly diagnosis. Analyzes quality data files, identifies root causes using 6-dimensional analysis (人机料法环测: Man/Machine/Material/Method/Environment/Measurement), and generates improvement solutions.

## Commands

### Full Stack (Docker)

```bash
cd deploy
docker-compose up --build        # Build and start all services
docker-compose up                # Start without rebuilding
docker-compose down              # Stop all services
```

### Backend (local dev)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (local dev)

```bash
cd frontend
npm install
npm run dev        # Dev server on port 3000 (proxies /api to localhost:8000)
npm run build      # Build to dist/
npm start          # Production Express server
```

## Architecture

### Request Flow

1. User uploads quality data file (Excel/PDF/image/Word) via `POST /api/upload/file`
2. `services/file_parser.py` parses the file using MinerU (PDFs/images/Word) or pandas (Excel), normalizes Chinese column names to English keys, validates that result columns (判定/结果/result) exist
3. `POST /api/diagnosis/analyze` triggers `agents/orchestrator.py` → `QualityDiagnosisOrchestrator` calls the Qwen LLM (ChatTongyi via DashScope) directly — **not** via AgentExecutor — to avoid compatibility issues
4. The orchestrator uses LangChain tools in `agents/tools.py`: data analysis, Milvus case similarity search, trend analysis
5. `POST /api/solution/generate` produces improvement recommendations

### Key Architectural Decisions

- **Direct LLM calls instead of AgentExecutor** — ChatTongyi compatibility workaround; orchestrator manually invokes tools and parses JSON responses with fallback handling
- **Milvus fallback** — `knowledge_base/milvus_client.py` has hardcoded fallback cases when the vector DB is unavailable
- **Multi-file merge** — Upload endpoint accepts multiple files; parser merges them before analysis
- **Frontend mock server** — `frontend/server.js` includes mock API endpoints for frontend-only development without a running backend

### Services (Docker Compose)

| Service | Port | Purpose |
|---|---|---|
| quality-backend | 8000 | FastAPI app |
| quality-frontend | 3000 | Vue 3 / Nginx |
| milvus-standalone | 19530 | Vector DB for case similarity |
| quality-postgres | 5432 | Relational data |
| milvus-etcd | 2379 | Milvus metadata |
| milvus-minio | 9000 | Milvus object storage |

### Environment Variables

Copy `backend/.env.example` to `backend/.env`. Key variables:

```
DASHSCOPE_API_KEY=      # Qwen/Tongyi LLM API key (required)
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530
POSTGRES_HOST=quality-postgres
POSTGRES_DB=quality_db
POSTGRES_USER=quality_user
POSTGRES_PASSWORD=...
MINERU_BACKEND=pipeline  # Document parsing backend
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=52428800  # 50MB
```

### Frontend API Client

`frontend/src/api/index.js` exports `uploadFile()`, `startDiagnosis()`, `generateSolution()`. The Vite dev proxy (`vite.config.js`) forwards `/api/*` to `http://localhost:8000`.

### File Upload Constraints

- Max size: 50 MB
- Allowed types: `.xlsx`, `.xls`, `.pdf`, `.jpg`, `.jpeg`, `.png`, `.docx`, `.doc`
- Quality data files must contain a result column (判定 / 结果 / result) or upload is rejected
