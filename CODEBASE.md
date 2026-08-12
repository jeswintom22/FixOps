# FixOps IQ codebase guide

FixOps IQ turns an incident title and raw log into a grounded SRE investigation. It analyzes signals, retrieves operational knowledge, produces a root cause, plans remediation, and stores a report with structured evidence.

`main.py` owns the FastAPI application. `POST /incidents` stores an incident. `POST /investigate` creates one queued `Investigation` protected by a PostgreSQL partial unique index, returns `202`, and schedules the pipeline. Clients poll `GET /investigations/{id}` and fetch `/investigations/{id}/report` after completion.

`app/agent/` contains `AgentOrchestrator` and five typed steps: log analysis, knowledge retrieval, root-cause analysis, remediation planning, and report generation. Low confidence triggers expanded retrieval and a retry; fewer than two remediation steps triggers a planning retry. Each execution is recorded in `StepExecution`.

`AgentState.to_report_payload()` serializes timeline entries, evidence references, remediation steps, confidence, and retry flags without converting structured data back into prose. `app/models/` defines database entities; `app/schemas/` defines public Pydantic contracts.

`app/services/ai.py` defines LLM/embedding contracts and Azure OpenAI, Azure Foundry, Ollama, and deterministic mock providers. `DBKnowledgeService` performs pgvector search, while `MockKnowledgeService` supports the offline demo.

`ui/` is a Streamlit client that polls asynchronous investigations and renders structured report fields. `scripts/demo_run.py` runs the pipeline in memory; `scripts/ingest_knowledge.py` loads the markdown knowledge base.

Use `alembic upgrade head` for schema changes. `docker-compose.yml` provides API and pgvector PostgreSQL. Settings come from `.env`; secrets are ignored by git.
