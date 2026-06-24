# FixOps IQ

>

FixOps IQ is an AI-powered SRE reasoning agent that investigates incidents end-to-end. Submit an error log, get back a structured root cause analysis, supporting evidence, and a ranked remediation plan — automatically.

---

## Microsoft IQ Integration — Foundry IQ

FixOps IQ integrates **Azure AI Foundry** (Foundry IQ) for semantic knowledge retrieval.

| Component | Provider |
|---|---|
| Semantic embeddings | Azure AI Foundry — `text-embedding-3-large` |
| Structured reasoning | Ollama (local) or Azure OpenAI |
| Evaluation / demo mode | `AI_PROVIDER=mock` — zero credentials needed |

The knowledge retrieval step embeds incident signals using `text-embedding-3-large` via the Azure AI Foundry endpoint, then performs cosine similarity search across runbooks, playbooks, and postmortems stored in PostgreSQL with `pgvector`. This is the core intelligence layer that grounds the agent's root cause reasoning in real operational knowledge.

---

## What it does

```
Incident submitted
       ↓
Log Analysis          — extracts error type, affected service, anomaly signals
       ↓
Knowledge Retrieval   — Azure AI Foundry embeddings search runbooks + postmortems
       ↓
Root Cause Analysis   — LLM reasoning with confidence score; retries with expanded context if < 0.75
       ↓
Remediation Planning  — ranked steps with kubectl commands; retries if fewer than 2 steps generated
       ↓
Report Generation     — structured report with executive summary, evidence, timeline
```

The agent makes real decisions at runtime:
- Severity HIGH/CRITICAL → fetches `top_k=8` knowledge chunks instead of 3
- Confidence score below threshold → automatically retries root cause with expanded context
- Thin remediation plan → automatically retries planning step

---

## Demo

The full demo runs in mock mode — no API keys or database needed.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirement.txt

$env:AI_PROVIDER="mock"
python scripts/demo_run.py
```

To run the full UI demo:

```powershell
# Terminal 1 — backend
$env:AI_PROVIDER="mock"
python -m uvicorn main:app --reload

# Terminal 2 — Streamlit UI
$env:AI_PROVIDER="mock"
$env:FIXOPS_API_URL="http://127.0.0.1:8000"
streamlit run ui/app.py
```

Open `http://localhost:8501` and submit this incident to see the full pipeline:

**Title:** `Payments checkout spike causing transaction timeouts`

**Raw Log:**
```
2026-06-11T09:14:03Z INFO payments-api checkout latency p95 crossed 4200ms region=ap-south-1
2026-06-11T09:16:18Z ERROR payments-api com.zaxxer.hikari.pool.HikariPool Connection is not available, request timed out after 30000ms
2026-06-11T09:16:21Z ERROR payments-api org.postgresql.util.PSQLException FATAL: sorry, too many clients already SQLSTATE 53300
2026-06-11T09:18:07Z WARN payments-api retry storm detected for authorize-payment requests trace=8d0c1
2026-06-11T09:20:11Z WARN payments-api readiness probe failed while inflight requests remained above threshold
```

**Severity:** `HIGH`

---

## Architecture

### Active backend

- `main.py` — FastAPI entrypoint, routes, lifecycle, exception handling
- `app/config.py` — environment-driven settings with split LLM/embedding provider support
- `app/agent/orchestrator.py` — multi-step agent with confidence-gated retry logic
- `app/agent/steps/` — five typed pipeline steps (log analysis → knowledge retrieval → root cause → remediation → report)
- `app/services/ai.py` — provider-agnostic LLM and embedding interfaces (Azure OpenAI, Azure Foundry, Ollama, Mock)
- `app/services/db_knowledge_service.py` — pgvector cosine similarity search via Azure AI Foundry embeddings
- `app/db/` — async SQLAlchemy engine and session management
- `app/models/` — PostgreSQL ORM models for incidents, investigations, reports, knowledge chunks
- `ui/` — Streamlit client

### Knowledge base

`knowledge_base/` contains runbooks, playbooks, and postmortems in markdown. The `scripts/ingest_knowledge.py` script chunks and embeds them into PostgreSQL via Azure AI Foundry. The agent retrieves the most relevant chunks at investigation time using vector similarity.

### Folder structure

```
FixOps/
├── app/
│   ├── agent/          — orchestrator + 5 pipeline steps
│   ├── api/            — FastAPI dependency injection
│   ├── core/           — constants, logging
│   ├── db/             — async SQLAlchemy session
│   ├── models/         — ORM models
│   ├── schemas/        — Pydantic request/response schemas
│   └── services/       — AI providers, knowledge service, incident/report services
├── knowledge_base/
│   ├── runbooks/
│   ├── playbooks/
│   └── postmortems/
├── scripts/
│   ├── demo_run.py     — offline demo, no credentials needed
│   └── ingest_knowledge.py
├── ui/                 — Streamlit client
├── legacy/             — earlier Redis/RQ + SQLite prototype (not used)
├── main.py
└── requirement.txt
```

---

## Full setup (with real providers)

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ with `pgvector` (or use the Docker command below)
- Ollama installed with `qwen3:8b` pulled
- Azure AI Foundry endpoint with `text-embedding-3-large` deployed

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirement.txt
```

### PostgreSQL with pgvector

```powershell
docker run --name fixops-postgres `
  -e POSTGRES_USER=user `
  -e POSTGRES_PASSWORD=pass `
  -e POSTGRES_DB=fixops_iq `
  -p 5432:5432 `
  -d pgvector/pgvector:pg15
```

### Ollama

```powershell
ollama pull qwen3:8b
```

### Environment

Create `.env` from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Hybrid setup (Ollama for LLM, Azure AI Foundry for embeddings):

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fixops_iq
DB_ECHO=false
APP_ENV=development
LOG_LEVEL=INFO

LLM_PROVIDER=ollama
CHAT_MODEL=qwen3:8b
CHAT_DEPLOYMENT=qwen3:8b
OLLAMA_MODEL=qwen3:8b

EMBEDDING_PROVIDER=azure_openai
ENDPOINT=https://<your-resource>.openai.azure.com
API_KEY=<your-key>
API_VERSION=2024-02-01
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DEPLOYMENT=text-embedding-3-large

FIXOPS_API_URL=http://127.0.0.1:8000
```

Mock setup (no credentials):

```env
AI_PROVIDER=mock
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fixops_iq
```

### Ingest knowledge base

```powershell
python scripts/ingest_knowledge.py
```

### Run

```powershell
# Backend
python -m uvicorn main:app --reload

# Frontend (separate terminal)
$env:FIXOPS_API_URL="http://127.0.0.1:8000"
streamlit run ui/app.py
```

---

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/incidents` | Create an incident record |
| `POST` | `/investigate` | Run the full agent pipeline for an incident |
| `GET` | `/reports/{id}` | Fetch the structured investigation report |
| `GET` | `/healthz` | Database health check |

API docs available at `http://127.0.0.1:8000/docs` when running.

---

## Agentic reasoning features

- **Confidence-gated retry** — if root cause confidence score is below 0.75, the agent re-runs knowledge retrieval with expanded context and retries root cause analysis
- **Severity-adaptive retrieval** — HIGH/CRITICAL incidents fetch 8 knowledge chunks; MEDIUM/LOW fetch 3
- **Remediation retry** — if fewer than 2 remediation steps are generated, the planning step runs again automatically
- **Typed step outputs** — each pipeline step produces a typed dataclass result; the orchestrator passes structured state between steps
- **Mock mode** — fully deterministic pipeline with no external dependencies, suitable for evaluation and CI

---

## Observability

- All logs emitted as structured JSON to stdout
- `GET /healthz` verifies database reachability
- Unhandled exceptions are logged server-side and return sanitized 500 responses
- Investigation status tracked per step in PostgreSQL (`QUEUED → RUNNING → COMPLETED / FAILED`)
