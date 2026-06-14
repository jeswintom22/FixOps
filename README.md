# FixOps IQ

FixOps IQ is an incident investigation backend for SRE and operations workflows. It accepts incident submissions, runs a multi-step investigation pipeline, retrieves supporting operational knowledge, and produces a structured report for root cause analysis and remediation planning.

The active production path in this repository is the FastAPI backend in `main.py` and `app/`, plus the Streamlit client in `ui/`. The root-level Redis/RQ prototype is still present for reference, but it is legacy code and not the primary runtime path.

## Architecture

### Active backend

- `main.py`: FastAPI entrypoint, API routes, lifecycle, health check, and exception handling
- `app/config.py`: environment-driven settings with validation
- `app/db/`: async SQLAlchemy engine and session management
- `app/models/`: PostgreSQL ORM models for incidents, investigations, reports, and knowledge chunks
- `app/services/`: service layer for incidents, investigations, reports, provider-agnostic AI services, and knowledge retrieval
- `app/agent/`: multi-step orchestration for log analysis, knowledge retrieval, root cause analysis, remediation planning, and report generation
- `ui/`: Streamlit client that drives the API workflow

### Legacy prototype

- `database.py`, `queue_config.py`, `worker_tasks.py`, `services/`, and `state/` represent an earlier SQLite and Redis/RQ prototype
- They are not used by the active FastAPI investigation flow, but they remain in the repository and still compile

## Features

- Incident creation and validation
- Investigation orchestration with typed step outputs
- Configurable chat and embedding providers via DI
- Mock AI and knowledge services for deterministic local demos
- PostgreSQL persistence with `pgvector`
- Structured JSON logging
- Health endpoint at `GET /healthz`
- Streamlit UI for manual end-to-end workflows

## Folder Structure

```text
FixOps/
|-- app/
|   |-- agent/
|   |-- api/
|   |-- core/
|   |-- db/
|   |-- models/
|   |-- schemas/
|   `-- services/
|-- docs/
|-- knowledge_base/
|-- scripts/
|-- ui/
|-- main.py
|-- requirement.txt
`-- RUNNING.md
```

## Local Setup

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ with `pgvector`
- AI provider credentials for the active backend

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirement.txt
```

## Environment Setup

Create a `.env` file from `.env.example` and fill in the required values.

```powershell
Copy-Item .env.example .env
```

Required variables for the active backend:

- `DATABASE_URL`
- `DB_ECHO`
- `APP_ENV`
- `LOG_LEVEL`
- `AI_PROVIDER`
- `ENDPOINT`
- `API_KEY`
- `API_VERSION`
- `CHAT_MODEL` or `CHAT_DEPLOYMENT`
- `EMBEDDING_MODEL` or `EMBEDDING_DEPLOYMENT`

Optional variable for the Streamlit UI:

- `FIXOPS_API_URL`

## Database Setup

### PostgreSQL

The app expects PostgreSQL with the `vector` extension available.

Example local database:

```powershell
docker run --name fixops-postgres `
  -e POSTGRES_USER=user `
  -e POSTGRES_PASSWORD=pass `
  -e POSTGRES_DB=fixops_iq `
  -p 5432:5432 `
  -d postgres:15
```

Install `pgvector` in that database before starting the backend. On startup, the app will run `CREATE EXTENSION IF NOT EXISTS vector` and create tables from the ORM metadata.

## Running Backend

```powershell
python -m uvicorn main:app --reload
```

Useful endpoints:

- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/healthz`

## Running Frontend

Set the API base URL and start Streamlit:

```powershell
$env:FIXOPS_API_URL="http://127.0.0.1:8000"
streamlit run ui/app.py
```

## API Endpoints

- `POST /incidents`
  Creates an incident record.
- `POST /investigate`
  Starts an investigation for an incident unless one is already active.
- `GET /reports/{id}`
  Fetches the final structured report for an investigation.
- `GET /healthz`
  Executes a database health check.

### Example workflow

Create an incident:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/incidents" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"title":"Payments timeout","description":"Checkout failures observed","raw_log":"2026-06-12T14:22:11Z ERROR payments-api request timed out","severity":"HIGH"}'
```

Start an investigation:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/investigate" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"incident_id":"<incident_id>"}'
```

Fetch the report:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/reports/<report_id>"
```

## Demo Workflow

For a deterministic end-to-end run without a live database or external AI dependency:

```powershell
.\.venv\Scripts\python scripts\demo_run.py
```

This uses `MockAIService` and `MockKnowledgeService` to exercise the agent pipeline locally.

## Observability Notes

- Application logs are emitted as JSON to stdout
- `GET /healthz` verifies database reachability
- Unexpected application exceptions are logged server-side and return sanitized `500` responses

Recommended next production steps:

- Send JSON logs to a central sink such as Datadog, ELK, or Azure Monitor
- Add request IDs and distributed tracing
- Add metrics for investigation latency, failure rate, and external AI call duration
- Add Alembic migrations before deploying to shared environments

## Future Roadmap

- Replace ORM `create_all` with managed migrations
- Persist per-step investigation audit records instead of in-memory state only
- Add authenticated API access and rate limiting
- Move long-running investigations to background workers instead of request/response execution
- Replace the mock knowledge service with database-backed retrieval
