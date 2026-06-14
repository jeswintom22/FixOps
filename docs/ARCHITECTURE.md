# FixOps IQ — Architecture Design
### Microsoft Agents League 2026 · Reasoning Agents Track

> **Lead Architect Review**
> The existing repo (`jeswintom22/FixOps`) is a flat-structure prototype: `main.py`,
> `database.py`, `queue_config.py`, `worker_tasks.py`, SQLite, RQ workers, pluggable
> Ollama/OpenAI providers. This document evolves that foundation into a production-grade
> reasoning agent with PostgreSQL, Azure AI Foundry, a proper agent pipeline, and a
> structured knowledge retrieval layer — without discarding what already works.

---

## Table of Contents

1. [Folder Structure](#1-folder-structure)
2. [Database Schema](#2-database-schema)
3. [Service Boundaries](#3-service-boundaries)
4. [API Contracts](#4-api-contracts)
5. [Agent Workflow](#5-agent-workflow)

---

## 1. Folder Structure

The existing flat root layout is refactored into domain-grouped packages under `app/`.
Everything that already exists is preserved and migrated — nothing is deleted.

```
fixops-iq/
│
├── app/
│   │
│   ├── main.py                        # FastAPI app factory, lifespan, middleware
│   ├── config.py                      # Settings via pydantic-settings (.env driven)
│   │
│   ├── api/                           # Transport layer — HTTP only
│   │   ├── deps.py                    # Shared FastAPI dependencies (db session, auth)
│   │   └── v1/
│   │       ├── router.py              # Aggregates all endpoint routers
│   │       └── endpoints/
│   │           ├── incidents.py       # POST /incidents, GET /incidents/{id}
│   │           ├── investigations.py  # POST /investigate
│   │           └── reports.py         # GET /reports/{id}
│   │
│   ├── agent/                         # Core reasoning agent — the hackathon centrepiece
│   │   ├── orchestrator.py            # Entry point: runs the multi-step workflow
│   │   ├── state.py                   # AgentState dataclass passed between steps
│   │   ├── steps/                     # One module per workflow step
│   │   │   ├── base.py                # Abstract Step interface
│   │   │   ├── log_analyzer.py        # Step 1 — parse & signal extraction
│   │   │   ├── knowledge_retriever.py # Step 2 — RAG from knowledge base
│   │   │   ├── root_cause_analyzer.py # Step 3 — multi-hop reasoning
│   │   │   ├── remediation_planner.py # Step 4 — ranked fix recommendations
│   │   │   └── report_generator.py   # Step 5 — structured report assembly
│   │   └── prompts/                   # Versioned prompt templates (plain text)
│   │       ├── log_analysis.txt
│   │       ├── knowledge_query.txt
│   │       ├── root_cause.txt
│   │       ├── remediation.txt
│   │       └── report_assembly.txt
│   │
│   ├── services/                      # Business logic — no HTTP, no DB queries
│   │   ├── incident_service.py        # Create, retrieve, update incident records
│   │   ├── investigation_service.py   # Enqueue, status, cancel investigations
│   │   ├── knowledge_service.py       # Chunk ingestion, semantic search, retrieval
│   │   ├── report_service.py          # Persist and fetch structured reports
│   │   └── azure_ai_service.py        # Azure AI Foundry client wrapper
│   │
│   ├── models/                        # SQLAlchemy ORM — PostgreSQL tables
│   │   ├── base.py                    # DeclarativeBase, TimestampMixin
│   │   ├── incident.py
│   │   ├── investigation.py
│   │   ├── investigation_step.py
│   │   ├── evidence.py
│   │   ├── root_cause.py
│   │   ├── remediation.py
│   │   ├── report.py
│   │   └── knowledge_chunk.py
│   │
│   ├── schemas/                       # Pydantic v2 — request/response contracts
│   │   ├── incident.py
│   │   ├── investigation.py
│   │   ├── report.py
│   │   └── common.py                  # Shared envelope types (PaginatedResponse, etc.)
│   │
│   ├── db/
│   │   ├── session.py                 # Async SQLAlchemy engine + session factory
│   │   └── migrations/                # Alembic
│   │       ├── env.py
│   │       └── versions/
│   │           └── 0001_initial.py    # Full schema creation migration
│   │
│   ├── workers/                       # Migrated from root-level worker_tasks.py
│   │   ├── queue_config.py            # Redis/RQ queues (migrated from existing)
│   │   ├── investigation_worker.py    # Picks up investigation jobs, runs orchestrator
│   │   └── tasks.py                   # RQ task definitions
│   │
│   ├── detectors/                     # Migrated from services/detectors/
│   │   ├── anomaly_detector.py        # Existing anomaly detection logic (preserved)
│   │   ├── pattern_matcher.py         # Log pattern matching (preserved)
│   │   └── signal_extractor.py        # New: structured signal output for agent
│   │
│   └── core/
│       ├── exceptions.py              # Domain exceptions → HTTP error mapping
│       ├── logging.py                 # Structured JSON logging setup
│       └── constants.py               # Enums: IncidentStatus, InvestigationStatus, etc.
│
├── knowledge_base/                    # Static knowledge documents loaded at startup
│   ├── runbooks/                      # Operational runbooks (.md files)
│   ├── playbooks/                     # Remediation playbooks (.md files)
│   └── postmortems/                   # Historical incident postmortems (.md files)
│
├── tests/
│   ├── unit/
│   │   ├── agent/                     # Per-step unit tests with mocked LLM calls
│   │   └── services/
│   └── integration/
│       └── api/                       # End-to-end API tests against test DB
│
├── docker/
│   ├── Dockerfile                     # API service
│   └── Dockerfile.worker              # RQ worker service
│
├── docker-compose.yml                 # Brings up: api, worker, postgres, redis
├── alembic.ini
├── .env.example
├── requirement.txt                    # Existing file — extended with new deps
└── README.md
```

### Key Migration Notes

| Existing file | Destination in FixOps IQ | Action |
|---|---|---|
| `main.py` | `app/main.py` | Move, add lifespan hook for DB init |
| `database.py` (SQLite) | `app/db/session.py` + migrations | Replace with async SQLAlchemy + PostgreSQL |
| `queue_config.py` | `app/workers/queue_config.py` | Move, queues renamed for clarity |
| `worker_tasks.py` | `app/workers/tasks.py` | Move, refactor to call orchestrator |
| `services/detectors/` | `app/detectors/` | Move, add `signal_extractor.py` |
| `services/ai/` | `app/services/azure_ai_service.py` | Replace provider factory with Azure AI Foundry client |
| `services/actions/` | `app/services/investigation_service.py` | Merge action logic into investigation service |
| `state/` | `app/agent/state.py` | Migrate state management to typed dataclass |

---

## 2. Database Schema

**Engine:** PostgreSQL 15+
**ORM:** SQLAlchemy 2.x (async)
**Migrations:** Alembic

All tables carry `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`,
`created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`,
and `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`.

---

### Table: `incidents`

Stores the raw incident input and its lifecycle status.

```sql
CREATE TABLE incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    description     TEXT,
    raw_log         TEXT NOT NULL,          -- original log or error string submitted
    severity        VARCHAR(20) NOT NULL    -- CRITICAL | HIGH | MEDIUM | LOW
                    DEFAULT 'MEDIUM',
    status          VARCHAR(30) NOT NULL    -- OPEN | INVESTIGATING | RESOLVED | CLOSED
                    DEFAULT 'OPEN',
    source          VARCHAR(100),           -- e.g. "prometheus", "datadog", "manual"
    service_name    VARCHAR(100),           -- affected service, if known
    environment     VARCHAR(50),            -- prod | staging | dev
    tags            JSONB DEFAULT '[]',
    metadata        JSONB DEFAULT '{}',     -- arbitrary key-value from caller
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_incidents_status   ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_created  ON incidents(created_at DESC);
```

---

### Table: `investigations`

One investigation job per incident (can be re-triggered).

```sql
CREATE TABLE investigations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id     UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    status          VARCHAR(30) NOT NULL    -- QUEUED | RUNNING | COMPLETED | FAILED
                    DEFAULT 'QUEUED',
    current_step    VARCHAR(50),            -- name of the step currently executing
    error_message   TEXT,                  -- populated on FAILED
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_investigations_incident ON investigations(incident_id);
CREATE INDEX idx_investigations_status   ON investigations(status);
```

---

### Table: `investigation_steps`

Audit log of every agent step — input context, LLM output, latency.

```sql
CREATE TABLE investigation_steps (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    step_name        VARCHAR(50) NOT NULL,  -- LOG_ANALYSIS | KNOWLEDGE_RETRIEVAL |
                                            -- ROOT_CAUSE | REMEDIATION | REPORT
    step_order       INTEGER NOT NULL,
    status           VARCHAR(20) NOT NULL   -- PENDING | RUNNING | DONE | FAILED
                     DEFAULT 'PENDING',
    input_context    JSONB,                 -- what was passed into the step
    output           JSONB,                 -- structured output from the step
    tokens_used      INTEGER,
    latency_ms       INTEGER,
    error            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inv_steps_investigation ON investigation_steps(investigation_id);
CREATE INDEX idx_inv_steps_order         ON investigation_steps(investigation_id, step_order);
```

---

### Table: `root_causes`

Structured root cause analysis result, linked to an investigation.

```sql
CREATE TABLE root_causes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    primary_cause    TEXT NOT NULL,         -- human-readable primary cause
    contributing_factors JSONB DEFAULT '[]', -- list of contributing cause strings
    confidence_score FLOAT,                -- 0.0 – 1.0
    reasoning_chain  TEXT,                 -- chain-of-thought trace from LLM
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_root_causes_investigation ON root_causes(investigation_id);
```

---

### Table: `evidence_items`

Individual pieces of supporting evidence for a root cause.

```sql
CREATE TABLE evidence_items (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    root_cause_id    UUID NOT NULL REFERENCES root_causes(id) ON DELETE CASCADE,
    evidence_type    VARCHAR(30) NOT NULL,  -- LOG_PATTERN | KNOWLEDGE_MATCH |
                                            -- ANOMALY_SIGNAL | HISTORICAL_MATCH
    content          TEXT NOT NULL,
    source_ref       TEXT,                  -- file name, runbook title, log line
    relevance_score  FLOAT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_root_cause ON evidence_items(root_cause_id);
```

---

### Table: `remediation_plans`

Ranked list of recommended remediation actions.

```sql
CREATE TABLE remediation_plans (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    summary          TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_remediation_investigation ON remediation_plans(investigation_id);
```

---

### Table: `remediation_steps`

Individual ordered steps within a remediation plan.

```sql
CREATE TABLE remediation_steps (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    remediation_plan_id UUID NOT NULL REFERENCES remediation_plans(id) ON DELETE CASCADE,
    step_order          INTEGER NOT NULL,
    action              TEXT NOT NULL,          -- "Increase connection pool size to 20"
    rationale           TEXT,
    risk_level          VARCHAR(20)             -- LOW | MEDIUM | HIGH
                        DEFAULT 'LOW',
    is_automated        BOOLEAN DEFAULT FALSE,  -- can this be auto-applied?
    command_hint        TEXT,                   -- optional CLI or API command
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rem_steps_plan  ON remediation_steps(remediation_plan_id);
CREATE INDEX idx_rem_steps_order ON remediation_steps(remediation_plan_id, step_order);
```

---

### Table: `reports`

Final structured investigation report.

```sql
CREATE TABLE reports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id    UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    incident_id         UUID NOT NULL REFERENCES incidents(id),
    title               TEXT NOT NULL,
    executive_summary   TEXT NOT NULL,
    incident_summary    TEXT NOT NULL,
    root_cause_section  TEXT NOT NULL,
    evidence_section    TEXT NOT NULL,
    remediation_section TEXT NOT NULL,
    timeline            JSONB DEFAULT '[]',     -- [{timestamp, event}]
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    format_version      VARCHAR(10) DEFAULT '1.0'
);

CREATE UNIQUE INDEX idx_reports_investigation ON reports(investigation_id);
CREATE INDEX        idx_reports_incident      ON reports(incident_id);
```

---

### Table: `knowledge_chunks`

Knowledge base entries loaded from runbooks, playbooks, postmortems.
Used by the retrieval step for semantic search.

```sql
CREATE TABLE knowledge_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_file     VARCHAR(255) NOT NULL,     -- e.g. "runbooks/db_connection.md"
    chunk_index     INTEGER NOT NULL,          -- position within the source file
    category        VARCHAR(50),               -- RUNBOOK | PLAYBOOK | POSTMORTEM
    content         TEXT NOT NULL,
    keywords        JSONB DEFAULT '[]',        -- extracted keywords for BM25 fallback
    embedding       vector(1536),              -- Azure OpenAI text-embedding-ada-002
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pgvector index for ANN search
CREATE INDEX idx_knowledge_embedding ON knowledge_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_knowledge_source    ON knowledge_chunks(source_file);
CREATE INDEX idx_knowledge_category  ON knowledge_chunks(category);
```

> **Note:** Requires the `pgvector` PostgreSQL extension (`CREATE EXTENSION vector`).
> This enables semantic retrieval without an external vector store.

---

### Entity Relationship Overview

```
incidents
    └─── investigations (1:1 active, 1:many historical)
              ├─── investigation_steps  (1:many, ordered)
              ├─── root_causes          (1:1)
              │         └─── evidence_items  (1:many)
              ├─── remediation_plans    (1:1)
              │         └─── remediation_steps (1:many, ordered)
              └─── reports              (1:1)

knowledge_chunks  (standalone, queried by retrieval step)
```

---

## 3. Service Boundaries

Each service has a single owner domain. Services communicate through explicit method
calls — never through direct DB access across domains.

---

### `IncidentService`

**Owns:** `incidents` table
**Responsibility:** Accept raw log input, normalize it, persist the incident record,
drive status transitions.

**Public interface:**

| Method | Description |
|---|---|
| `create(payload)` | Validate and persist a new incident |
| `get_by_id(id)` | Fetch incident by UUID |
| `update_status(id, status)` | Transition incident status |
| `list(filters, pagination)` | Filtered list view |

**Does NOT:** call the agent, trigger workers, or know about reports.

---

### `InvestigationService`

**Owns:** `investigations` table, `investigation_steps` table
**Responsibility:** Create investigation jobs, enqueue them to Redis, poll and update
step progress, surface status to the API layer.

**Public interface:**

| Method | Description |
|---|---|
| `create_for_incident(incident_id)` | Create an investigation record and enqueue it |
| `get_by_id(id)` | Fetch investigation + steps |
| `update_step(investigation_id, step_name, output)` | Record a completed step |
| `mark_completed(id)` | Final status transition on success |
| `mark_failed(id, error)` | Final status transition on failure |

**Does NOT:** run reasoning logic. Purely orchestrates persistence and queueing.

---

### `AzureAIService`

**Owns:** Azure AI Foundry API connection
**Responsibility:** Wrap all calls to Azure AI Foundry — chat completions, embeddings.
Provides a single, testable interface so every agent step talks to one client.

**Public interface:**

| Method | Description |
|---|---|
| `chat_complete(system_prompt, user_prompt, response_format)` | Single LLM turn |
| `embed(text)` | Generate a 1536-dim embedding for knowledge retrieval |
| `structured_complete(prompt, schema)` | Chat completion with JSON schema enforcement |

**Does NOT:** know about incidents, steps, or reports. Pure infrastructure adapter.

---

### `KnowledgeService`

**Owns:** `knowledge_chunks` table
**Responsibility:** Load knowledge base documents into chunks at startup, generate
embeddings, serve hybrid semantic + keyword search queries.

**Public interface:**

| Method | Description |
|---|---|
| `ingest_documents(directory)` | Chunk, embed, and persist all documents in a dir |
| `search(query, top_k, category_filter)` | Hybrid search → ranked list of chunks |
| `get_chunk_by_id(id)` | Fetch a specific chunk |

**Search strategy:** cosine similarity on `embedding` vector as primary signal;
keyword overlap on `keywords` JSONB as tie-breaker (BM25-style fallback when
pgvector confidence is low).

---

### `ReportService`

**Owns:** `reports` table
**Responsibility:** Assemble and persist the final structured report from agent output.

**Public interface:**

| Method | Description |
|---|---|
| `create(investigation_id, report_data)` | Persist assembled report |
| `get_by_id(id)` | Fetch report |
| `get_by_investigation(investigation_id)` | Lookup report from investigation context |

**Does NOT:** generate content. It receives the fully-assembled report dict from the
agent and persists it.

---

### `WorkerService` (RQ-based)

**Owns:** Redis queue configuration, worker entrypoint
**Responsibility:** Dequeue investigation jobs, invoke the `AgentOrchestrator`, handle
retries and dead-letter on failure.

**Queue layout:**

| Queue name | Purpose |
|---|---|
| `investigations.high` | Critical-severity incidents — processed first |
| `investigations.normal` | Medium/low severity incidents |
| `investigations.retry` | Failed jobs awaiting retry |

**Does NOT:** contain any reasoning logic. It is a thin runner that calls
`AgentOrchestrator.run(investigation_id)`.

---

### `AgentOrchestrator`

**Owns:** multi-step reasoning pipeline
**Responsibility:** Coordinate the five agent steps in sequence. Manages `AgentState`,
persists intermediate outputs via `InvestigationService`, and passes accumulated
context forward to each step.

**This is not a service in the dependency-injection sense — it is a stateful workflow
runner, instantiated fresh per job by the worker.**

---

## 4. API Contracts

**Base path:** `/api/v1`
**Auth:** Bearer token (header: `Authorization: Bearer <token>`)
**Content-Type:** `application/json`
**Errors:** All errors follow `{ "error": { "code": str, "message": str, "detail": any } }`

---

### `POST /api/v1/incidents`

Submit a new incident or error log for tracking.

**Request body:**

```json
{
  "title": "Database connection timeout in payments service",
  "raw_log": "ERROR 2026-06-11T14:23:01Z [payments] psycopg2.OperationalError: could not connect to server: Connection timed out\n\tIs the server running on host 'db-prod-01' (10.0.1.5) and accepting\n\tTCP/IP connections on port 5432?",
  "severity": "HIGH",
  "service_name": "payments",
  "environment": "prod",
  "source": "datadog",
  "tags": ["database", "postgres", "payments"],
  "metadata": {
    "region": "us-east-1",
    "host": "db-prod-01"
  }
}
```

**Field rules:**

| Field | Type | Required | Values |
|---|---|---|---|
| `title` | string | Yes | max 500 chars |
| `raw_log` | string | Yes | raw log text or error string |
| `severity` | string | No | `CRITICAL` `HIGH` `MEDIUM` `LOW` — default `MEDIUM` |
| `service_name` | string | No | — |
| `environment` | string | No | `prod` `staging` `dev` |
| `source` | string | No | origin system |
| `tags` | string[] | No | — |
| `metadata` | object | No | arbitrary key-value |

**Response `201 Created`:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Database connection timeout in payments service",
  "status": "OPEN",
  "severity": "HIGH",
  "service_name": "payments",
  "environment": "prod",
  "created_at": "2026-06-11T14:23:05Z"
}
```

**Errors:** `400 Bad Request` (validation), `422 Unprocessable Entity` (schema mismatch)

---

### `GET /api/v1/incidents/{incident_id}`

Retrieve a full incident record.

**Path params:** `incident_id` — UUID

**Response `200 OK`:**

```json
{
  "id": "a1b2c3d4-...",
  "title": "Database connection timeout in payments service",
  "description": null,
  "raw_log": "ERROR 2026-06-11T...",
  "severity": "HIGH",
  "status": "INVESTIGATING",
  "service_name": "payments",
  "environment": "prod",
  "source": "datadog",
  "tags": ["database", "postgres", "payments"],
  "metadata": { "region": "us-east-1", "host": "db-prod-01" },
  "created_at": "2026-06-11T14:23:05Z",
  "updated_at": "2026-06-11T14:23:10Z"
}
```

**Errors:** `404 Not Found`

---

### `POST /api/v1/investigate`

Trigger an investigation for an existing incident. This is an async operation —
it enqueues the agent workflow and returns immediately.

**Request body:**

```json
{
  "incident_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "priority": "high"
}
```

**Field rules:**

| Field | Type | Required | Values |
|---|---|---|---|
| `incident_id` | UUID string | Yes | must reference an existing incident |
| `priority` | string | No | `high` `normal` — default matches incident severity |

**Response `202 Accepted`:**

```json
{
  "investigation_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
  "incident_id": "a1b2c3d4-...",
  "status": "QUEUED",
  "queue": "investigations.high",
  "created_at": "2026-06-11T14:23:15Z",
  "status_url": "/api/v1/investigations/f9e8d7c6-.../status"
}
```

**Errors:** `404` (incident not found), `409 Conflict` (investigation already running for this incident)

---

### `GET /api/v1/investigations/{investigation_id}/status`

Poll the live status of an in-progress investigation, including which step is running.

**Response `200 OK`:**

```json
{
  "investigation_id": "f9e8d7c6-...",
  "incident_id": "a1b2c3d4-...",
  "status": "RUNNING",
  "current_step": "ROOT_CAUSE_ANALYSIS",
  "steps": [
    { "step_name": "LOG_ANALYSIS",      "step_order": 1, "status": "DONE",    "latency_ms": 1240 },
    { "step_name": "KNOWLEDGE_RETRIEVAL","step_order": 2, "status": "DONE",    "latency_ms": 890  },
    { "step_name": "ROOT_CAUSE_ANALYSIS","step_order": 3, "status": "RUNNING", "latency_ms": null },
    { "step_name": "REMEDIATION",       "step_order": 4, "status": "PENDING",  "latency_ms": null },
    { "step_name": "REPORT_GENERATION", "step_order": 5, "status": "PENDING",  "latency_ms": null }
  ],
  "started_at": "2026-06-11T14:23:18Z",
  "completed_at": null
}
```

---

### `GET /api/v1/reports/{report_id}`

Retrieve the final structured investigation report.

**Path params:** `report_id` — UUID

**Response `200 OK`:**

```json
{
  "id": "c3d4e5f6-...",
  "investigation_id": "f9e8d7c6-...",
  "incident_id": "a1b2c3d4-...",
  "title": "Investigation Report — Database Connection Timeout — payments — 2026-06-11",
  "generated_at": "2026-06-11T14:25:44Z",
  "executive_summary": "The payments service experienced repeated connection timeouts to the primary PostgreSQL instance db-prod-01 due to connection pool exhaustion compounded by a long-running migration query.",
  "incident_summary": {
    "service": "payments",
    "environment": "prod",
    "first_seen": "2026-06-11T14:20:00Z",
    "severity": "HIGH",
    "affected_components": ["payments-api", "db-prod-01"]
  },
  "root_cause_analysis": {
    "primary_cause": "Connection pool exhausted: max_connections (10) reached due to a blocking migration query holding locks for 8+ minutes.",
    "contributing_factors": [
      "Default SQLAlchemy pool_size=5 with overflow=5 — insufficient for traffic spike",
      "Migration script lacked a statement_timeout guard",
      "No circuit breaker configured on the payments client"
    ],
    "confidence_score": 0.91
  },
  "supporting_evidence": [
    {
      "type": "LOG_PATTERN",
      "content": "14 occurrences of 'remaining connection slots are reserved for non-replication superuser' within 4 minutes",
      "source_ref": "raw_log:lines 12-26",
      "relevance_score": 0.97
    },
    {
      "type": "KNOWLEDGE_MATCH",
      "content": "Runbook DB-003: Connection pool exhaustion — symptoms include OperationalError on connect, pg_stat_activity showing idle-in-transaction sessions.",
      "source_ref": "runbooks/db_connection_pool.md",
      "relevance_score": 0.88
    }
  ],
  "remediation_recommendations": [
    {
      "step_order": 1,
      "action": "Immediately terminate the blocking migration query",
      "command_hint": "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND query_start < NOW() - INTERVAL '5 minutes';",
      "risk_level": "LOW",
      "is_automated": false
    },
    {
      "step_order": 2,
      "action": "Increase pool_size to 20 and pool_timeout to 30s in payments service config",
      "risk_level": "LOW",
      "is_automated": false
    },
    {
      "step_order": 3,
      "action": "Add statement_timeout = '30s' to migration sessions",
      "risk_level": "LOW",
      "is_automated": false
    },
    {
      "step_order": 4,
      "action": "Implement a circuit breaker (e.g. tenacity) on all DB calls in payments-api",
      "risk_level": "MEDIUM",
      "is_automated": false
    }
  ],
  "timeline": [
    { "timestamp": "2026-06-11T14:14:00Z", "event": "Migration job started on db-prod-01" },
    { "timestamp": "2026-06-11T14:20:00Z", "event": "First connection timeout logged in payments-api" },
    { "timestamp": "2026-06-11T14:23:01Z", "event": "Incident submitted to FixOps IQ" },
    { "timestamp": "2026-06-11T14:25:44Z", "event": "Investigation report generated" }
  ]
}
```

**Errors:** `404 Not Found`, `202 Accepted` (investigation still running — report not ready)

---

## 5. Agent Workflow

The `AgentOrchestrator` runs a linear, stateful pipeline. Each step receives the
accumulated `AgentState` from all prior steps and appends its own output before
passing it forward.

---

### AgentState (passed between steps)

```
AgentState {
  investigation_id:  UUID
  incident_id:       UUID
  raw_log:           str
  incident_metadata: dict

  # Populated progressively by each step:
  log_signals:       LogSignals | None
  knowledge_chunks:  list[KnowledgeChunk] | None
  root_cause:        RootCauseResult | None
  remediation:       RemediationResult | None
  report:            ReportResult | None
}
```

---

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RQ Worker Process                           │
│                                                                     │
│  dequeue(investigation_id)                                          │
│          │                                                          │
│          ▼                                                          │
│  ┌───────────────────┐                                              │
│  │ AgentOrchestrator │  ← loads incident from DB                   │
│  │  .run(inv_id)     │  ← initialises AgentState                   │
│  └────────┬──────────┘                                              │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  STEP 1 — Log Analysis                                      │   │
│  │                                                             │   │
│  │  Input:  raw_log (string)                                   │   │
│  │  Action: AzureAIService.structured_complete(                │   │
│  │            prompt=log_analysis.txt + raw_log,               │   │
│  │            schema=LogSignalsSchema                          │   │
│  │          )                                                  │   │
│  │  Output: LogSignals {                                       │   │
│  │            error_type, affected_service, key_terms,         │   │
│  │            anomaly_signals[], timestamp_range,              │   │
│  │            severity_assessment                              │   │
│  │          }                                                  │   │
│  │  Persists: investigation_steps row (LOG_ANALYSIS, DONE)     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼  state.log_signals = LogSignals                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  STEP 2 — Knowledge Retrieval                               │   │
│  │                                                             │   │
│  │  Input:  log_signals.key_terms + error_type                 │   │
│  │  Action: AzureAIService.embed(query_text)                   │   │
│  │          → KnowledgeService.search(                         │   │
│  │              embedding, top_k=5,                            │   │
│  │              category_filter=[RUNBOOK, PLAYBOOK]            │   │
│  │            )                                                │   │
│  │          → KnowledgeService.search(                         │   │
│  │              embedding, top_k=3,                            │   │
│  │              category_filter=[POSTMORTEM]                   │   │
│  │            )                                                │   │
│  │  Output: list[KnowledgeChunk] — top 8 ranked by relevance  │   │
│  │  Persists: investigation_steps row (KNOWLEDGE_RETRIEVAL)    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼  state.knowledge_chunks = [KnowledgeChunk, ...]        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  STEP 3 — Root Cause Analysis                               │   │
│  │                                                             │   │
│  │  Input:  log_signals + knowledge_chunks (formatted context) │   │
│  │  Action: AzureAIService.structured_complete(                │   │
│  │            prompt=root_cause.txt                            │   │
│  │              + formatted(log_signals)                       │   │
│  │              + formatted(knowledge_chunks),                 │   │
│  │            schema=RootCauseSchema                           │   │
│  │          )                                                  │   │
│  │  Output: RootCauseResult {                                  │   │
│  │            primary_cause, contributing_factors[],           │   │
│  │            confidence_score, reasoning_chain,               │   │
│  │            evidence_refs[]                                  │   │
│  │          }                                                  │   │
│  │  Persists: root_causes row + evidence_items rows            │   │
│  │            investigation_steps row (ROOT_CAUSE_ANALYSIS)    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼  state.root_cause = RootCauseResult                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  STEP 4 — Remediation Planning                              │   │
│  │                                                             │   │
│  │  Input:  root_cause + knowledge_chunks (playbooks only)     │   │
│  │  Action: AzureAIService.structured_complete(                │   │
│  │            prompt=remediation.txt                           │   │
│  │              + formatted(root_cause)                        │   │
│  │              + formatted(playbook_chunks),                  │   │
│  │            schema=RemediationSchema                         │   │
│  │          )                                                  │   │
│  │  Output: RemediationResult {                                │   │
│  │            summary,                                         │   │
│  │            steps[]: {                                       │   │
│  │              order, action, rationale,                      │   │
│  │              risk_level, command_hint,                      │   │
│  │              is_automated                                   │   │
│  │            }                                                │   │
│  │          }                                                  │   │
│  │  Persists: remediation_plans + remediation_steps rows       │   │
│  │            investigation_steps row (REMEDIATION)            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼  state.remediation = RemediationResult                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  STEP 5 — Report Generation                                 │   │
│  │                                                             │   │
│  │  Input:  full AgentState (all prior outputs)                │   │
│  │  Action: AzureAIService.structured_complete(                │   │
│  │            prompt=report_assembly.txt                       │   │
│  │              + formatted(entire state),                     │   │
│  │            schema=ReportSchema                              │   │
│  │          )                                                  │   │
│  │  Output: ReportResult {                                     │   │
│  │            title, executive_summary,                        │   │
│  │            incident_summary, root_cause_section,            │   │
│  │            evidence_section, remediation_section,           │   │
│  │            timeline[]                                       │   │
│  │          }                                                  │   │
│  │  Persists: reports row                                      │   │
│  │            investigation_steps row (REPORT_GENERATION)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│           │                                                         │
│           ▼                                                         │
│  InvestigationService.mark_completed(investigation_id)             │
│  IncidentService.update_status(incident_id, "RESOLVED")            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Step Failure Handling

```
If any step raises an exception:
  └── InvestigationService.mark_failed(investigation_id, error_message)
  └── investigation_steps row updated to status=FAILED with error text
  └── RQ retries the full job up to 2 times (retry queue: investigations.retry)
  └── After max retries: investigation.status = FAILED (dead-letter)
  └── Incident status remains INVESTIGATING (not auto-resolved on failure)
```

Each step is designed to be idempotent — if a step's `investigation_steps` row
already exists with `status=DONE`, the orchestrator skips it. This makes retries
safe and avoids redundant LLM calls.

---

### Azure AI Foundry Integration Points

| Step | Azure AI Foundry capability used |
|---|---|
| Log Analysis | Azure OpenAI chat completions (GPT-4o) with structured output |
| Knowledge Retrieval | Azure OpenAI embeddings (text-embedding-ada-002) |
| Root Cause Analysis | Azure OpenAI chat completions with chain-of-thought prompt |
| Remediation Planning | Azure OpenAI chat completions with JSON schema enforcement |
| Report Generation | Azure OpenAI chat completions with full context window |

All calls route through `AzureAIService` which reads
`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and `AZURE_OPENAI_DEPLOYMENT`
from environment — zero provider code lives inside agent steps.

---

### Environment Variables Required

```
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/fixops_iq

# Redis
REDIS_URL=redis://redis:6379/0

# Azure AI Foundry
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-02-01

# App
APP_ENV=production
LOG_LEVEL=INFO
```

---

*FixOps IQ — Architecture v1.0 — Microsoft Agents League 2026*
