# FixOps IQ Run Instructions

## Overview

This repository contains the current FixOps IQ backend application and a Streamlit UI client.
The main backend is launched from `main.py` and depends on the `app/` package.

> Note: There is also an older prototype in the root directory (`queue_config.py`, `worker_tasks.py`, `database.py`) that uses Redis/RQ and SQLite. The instructions below describe the current backend and UI flow.

## Requirements

- Python 3.10 or newer (the active workspace is using Python 3.10.11)
- PostgreSQL database reachable from the app
- PostgreSQL `pgvector` extension installed and available
- Access to AI provider credentials for the current backend
- Internet access for the configured AI provider and optional UI assets
- Optional: Docker, if you want to run PostgreSQL locally in a container

## Install Python dependencies

From the repository root (`d:\projects\FixOps`):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirement.txt
```

If you encounter missing packages, install them manually:

```powershell
pip install fastapi uvicorn sqlalchemy asyncpg openai streamlit requests
```

## Configure environment variables

Create or update a `.env` file in the project root. For the current backend, the minimum required values are:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fixops_iq
DB_ECHO=false
APP_ENV=development
LOG_LEVEL=INFO
AI_PROVIDER=azure_openai
ENDPOINT=https://<your-provider-endpoint>
API_KEY=<your-provider-api-key>
API_VERSION=<your-provider-api-version>
CHAT_DEPLOYMENT=<your-chat-deployment-name>
EMBEDDING_DEPLOYMENT=<your-embedding-deployment-name>
```

### AI provider values

- `AI_PROVIDER`: one of `azure_openai`, `azure_foundry`, `ollama`, or `mock`
- `ENDPOINT`: provider endpoint or compatible base URL
- `API_KEY`: provider credential, if required
- `API_VERSION`: provider API version, if required
- `CHAT_MODEL` and `CHAT_DEPLOYMENT`: chat model identifier and optional deployment alias
- `EMBEDDING_MODEL` and `EMBEDDING_DEPLOYMENT`: embedding model identifier and optional deployment alias

## PostgreSQL and `pgvector`

The app uses SQLAlchemy with `asyncpg` and creates tables automatically.
It also executes `CREATE EXTENSION IF NOT EXISTS vector` on startup.
This means your PostgreSQL server must support and allow the `pgvector` extension.

If you want to run PostgreSQL locally with Docker, use:

```powershell
docker run --name fixops-postgres -e POSTGRES_USER=user -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=fixops_iq -p 5432:5432 -d postgres:15
```

Then install `pgvector` in that database if needed.

## Run the backend

From the repository root and with the virtual environment active:

```powershell
python -m uvicorn main:app --reload
```

Confirm the app is running by opening:

```text
http://127.0.0.1:8000/docs
```

If the API documentation appears, the backend is started successfully.

## Run the Streamlit UI

The Streamlit UI is located under `ui/`.
Set the backend URL and start the UI:

```powershell
$env:FIXOPS_API_URL="http://127.0.0.1:8000"
streamlit run ui/app.py
```

Open the Streamlit page shown in the terminal to interact with the FixOps IQ workflow.

## Basic workflow

1. Start the backend
2. Start the UI
3. Use the UI to submit an incident
4. The UI calls:
   - `POST /incidents`
   - `POST /investigate`
   - `GET /reports/{id}`

## API validation examples

Use any HTTP client to verify the API manually.

Create an incident:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/incidents" -Method Post -ContentType "application/json" -Body '{"title":"Test incident","description":"Test run","raw_log":"2026-06-12T14:22:11Z ERROR payments-api request timed out","severity":"HIGH"}'
```

Run an investigation:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/investigate" -Method Post -ContentType "application/json" -Body '{"incident_id":"<incident_id>"}'
```

Fetch a report:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/reports/<report_id>"
```

## Troubleshooting

- If the backend fails with `AI provider configuration is incomplete`, verify your `.env` values for the selected provider.
- If the backend cannot connect to PostgreSQL, verify `DATABASE_URL`, that PostgreSQL is running, and that the database accepts connections.
- If the startup fails while creating `vector`, ensure the `pgvector` extension is installed on PostgreSQL.
- If the UI cannot connect, verify `FIXOPS_API_URL` points to the running backend.

## Notes

- The current backend path is `main.py` and `app/`, not the old prototype in the root.
- The current `app/` backend resolves chat and embedding providers through `app/api/deps.py`, `app/services/ai_factory.py`, and `app/services/ai.py`.
- The root-level `services/ai/llm_factory.py` and `queue_config.py` appear to be part of an earlier version and are not used by `main.py`.
- The UI uses `ui/api.py` and `ui/config.py` to communicate with the backend.

## Optional local setup checklist

- [ ] Python 3.10 installed
- [ ] Virtual environment created and activated
- [ ] `pip install -r requirement.txt` completed
- [ ] PostgreSQL running and reachable
- [ ] `pgvector` extension enabled
- [ ] `.env` file configured with AI provider settings
- [ ] Backend running at `http://127.0.0.1:8000`
- [ ] Streamlit UI started with `FIXOPS_API_URL`
