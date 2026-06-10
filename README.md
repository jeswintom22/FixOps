# FixOps

FixOps is a small DevOps incident-detection prototype. It accepts logs through a
FastAPI API, processes them with Redis/RQ workers, detects anomalies, and can use
either Ollama or the OpenAI API to generate incident analysis.

It stores local data in SQLite (`logs.db`).

## What It Does

- Ingests application logs with `POST /ingest`
- Normalizes logs and adds missing timestamps or trace IDs
- Runs anomaly detection
- Sends anomalies to an AI provider for root-cause analysis
- Stores logs, analysis results, and action history
- Includes basic action logic for alerts, webhooks, and safe remediation stubs

## Project Structure

```text
main.py                         FastAPI app and routes
queue_config.py                 Redis/RQ queue setup
worker_tasks.py                 Log processing worker task
database.py                     SQLite tables and database helpers
services/detectors/             Anomaly detection logic
services/ai/                    AI prompts, provider factory, LLM providers
services/actions/               Alert/action decision logic
```

## Setup

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirement.txt
```

If dependencies are missing, install the core packages:

```powershell
pip install fastapi uvicorn redis rq pydantic python-dotenv openai ollama
```

Start Redis:

```powershell
docker run --name fixops-redis -p 6379:6379 redis
```

If the container already exists:

```powershell
docker start fixops-redis
```

## Configure AI Provider

FixOps uses `LLM_PROVIDER` to choose between Ollama and OpenAI.

Create a `.env` file in the project root.

### Use Ollama

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
```

Pull the model:

```powershell
ollama pull qwen3:8b
```

You can use a different Ollama model by changing `OLLAMA_MODEL`.

### Use OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Restart the API and workers after changing `.env`.

## Run

Start the API:

```powershell
python -m uvicorn main:app --reload
```

Start the log worker:

```powershell
rq worker logs --worker-class rq.worker.SimpleWorker
```

Start the analysis worker:

```powershell
rq worker analysis --worker-class rq.worker.SimpleWorker
```

Or run one worker for all queues:

```powershell
rq worker logs analysis actions --worker-class rq.worker.SimpleWorker
```

API URL:

```text
http://127.0.0.1:8000
```

## API Examples

Send logs:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/ingest" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{
    "logs": [
      {
        "level": "ERROR",
        "service": "payments",
        "message": "payment timeout while calling gateway",
        "metadata": {
          "region": "us-east-1"
        }
      }
    ]
  }'
```

Read logs:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/logs
```

Read AI analysis:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis
```

Read analysis for one trace:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/analysis/<trace_id>
```

Read action history:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/actions
```

## Notes

- Default AI provider is `ollama`.
- Redis must be running before workers start.
- `logs.db` is created automatically.
- Delete `logs.db` to reset local data.
- AI responses must be valid JSON because the providers parse model output with
  `json.loads`.

