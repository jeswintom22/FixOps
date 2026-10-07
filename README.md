# FixOps

A CLI-first AI SRE agent that turns logs into structured incident reports. It analyzes signals, retrieves operational knowledge from your runbooks, and produces a root cause, evidence, and ranked remediation plan.

## Quick start

```bash
pip install ".[local]"

# Index the built-in runbooks, playbooks, and postmortems
fixops ingest

# Analyze a log file
cat sample.log | fixops investigate --title "Payments timeout"
# or
fixops investigate --title "Payments timeout" sample.log
```

No database, no cloud credentials, and no Docker are required for the default `local` provider.

## What it does

```
Log input
    ↓
Log Analysis          → error type, affected service, severity
    ↓
Knowledge Retrieval   → keyword search over runbooks, playbooks, postmortems
    ↓
Root Cause Analysis   → primary cause, confidence, validated citations
    ↓
Remediation Planning  → ranked steps with risk labels and command hints
    ↓
Report Generation     → markdown report with timeline and evidence
```

The incident is marked `ANALYZED`, not resolved. You resolve it manually when the remediation is complete.

## Supported LLM providers

| Provider | How to enable | Notes |
|---|---|---|
| `local` (default) | `LLM_PROVIDER=local` | Zero credentials; uses the markdown knowledge base and rule-based matching. |
| `ollama` | `LLM_PROVIDER=ollama` `LLM_MODEL=qwen3:8b` | Local open-source models. |
| `openai` | `LLM_PROVIDER=openai` `API_KEY=...` `LLM_MODEL=gpt-4o-mini` | Any OpenAI-compatible endpoint. |
| `azure_openai` | `LLM_PROVIDER=azure_openai` `ENDPOINT=...` `API_KEY=...` `API_VERSION=...` | Azure OpenAI or Azure AI Foundry. |

Set the provider with environment variables or CLI flags:

```bash
fixops --llm-provider ollama --llm-model qwen3:8b investigate sample.log
```

## Optional server mode

Run FixOps as a small FastAPI server for team sharing:

```bash
pip install ".[server,ui,local]"
fixops server
```

Then start the Streamlit UI:

```bash
streamlit run ui/app.py
```

Server endpoints require `FIXOPS_API_KEY` as the `X-API-Key` header when set.

## CLI commands

```bash
fixops ingest                           # Index the knowledge base
fixops investigate sample.log           # Analyze a log file
fixops history                          # List past incidents
fixops show <incident-id>               # Show the latest report for an incident
fixops resolve <incident-id>            # Mark an incident as resolved
fixops server                           # Start the optional API server
```

## Safety

- Logs are redacted for secrets, API keys, emails, and IP addresses before being sent to any cloud LLM.
- Remediation command hints are displayed with a risk label and are never executed automatically.
- The server uses constant-time API key comparison and CORS origin restrictions.

## Project layout

```
fixops/
├── cli.py            # CLI entrypoint
├── config.py         # Settings
├── db.py             # SQLite models
├── knowledge/        # Markdown loader and keyword retriever
├── llm/              # LLM provider implementations
├── pipeline/         # Five-step agent orchestrator
├── repository.py     # Database operations
├── security/         # Log redaction
└── server/           # Optional FastAPI server
knowledge_base/       # Runbooks, playbooks, postmortems
ui/                   # Optional Streamlit client
```

## Development

```bash
pip install ".[dev,server,ui,local]"
ruff check .
mypy fixops/ ui/
pytest -q
```

## License

MIT
