# Running FixOps

## Requirements

- Python 3.10+
- No external database or vector store is required.
- Optional: Ollama for local LLMs; API key for OpenAI/Azure.

## Install

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install ".[local]"
```

For the optional server/UI:

```bash
pip install ".[server,ui,local]"
```

## Run locally

```bash
# One-time: index the built-in knowledge base
fixops ingest

# Analyze a log file
cat logs.txt | fixops investigate --title "Payments timeout"
```

## Run with Ollama

```bash
ollama pull qwen3:8b
fixops --llm-provider ollama --llm-model qwen3:8b investigate logs.txt
```

## Run the optional server

```bash
# Terminal 1
fixops server

# Terminal 2
streamlit run ui/app.py
```

Set `FIXOPS_API_KEY` to require authentication on the server and UI.

## Run with Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`. Use `docker compose exec api fixops ingest` to index the knowledge base.

## Troubleshooting

- If `fixops` is not found, ensure you installed with `pip install -e ".[local]"` and your virtual environment is active.
- Set `LOG_LEVEL=DEBUG` for verbose logging.
