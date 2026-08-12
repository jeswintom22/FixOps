# FixOps IQ shipped architecture

FixOps IQ is a FastAPI service backed by async SQLAlchemy and PostgreSQL/pgvector, with a Streamlit client.

## Runtime flow

1. `POST /incidents` validates and stores an incident.
2. `POST /investigate` creates one queued investigation and returns `202`.
3. A FastAPI background task runs the typed pipeline.
4. The UI polls `GET /investigations/{id}` and reads the final report after completion.

The pipeline in `app/agent/` performs log analysis, knowledge retrieval, root-cause analysis, remediation planning, and report generation. Retry decisions are stored as explicit fields, and every step has an audit row in `step_executions`.

## Boundaries

- `app/models/`: database entities and indexes.
- `app/schemas/`: public Pydantic request/response contracts.
- `app/services/`: persistence, knowledge retrieval, and provider interfaces.
- `app/agent/`: orchestration state and typed steps.
- `app/core/`: settings, constants, and JSON logging.
- `knowledge_base/`: markdown runbooks, playbooks, and postmortems.
- `ui/`: Streamlit client that consumes the API.
- `scripts/`: offline demo and knowledge ingestion.

Database schema changes are managed by Alembic. `create_all` remains available only as a local-development fallback.
