# FixOps System Architecture

## Core Flow

Signal Sources
↓
Ingestion Layer
↓
Queue Layer
↓
Detection Layer
↓
Correlation Layer
↓
Incident Memory
↓
Agent Layer
↓
Coordinator Agent
↓
Decision Engine
↓
Action Engine
↓
Verification Engine
↓
Learning Layer

---

## Layer Responsibilities

### Signal Sources

- Logs
- Metrics
- Traces
- Deployments
- Alerts
- Health events

### Ingestion Layer

Responsibilities:

- Receive signals
- Validate payloads
- Normalize data
- Generate trace IDs

### Queue Layer

Responsibilities:

- Decouple ingestion
- Enable async processing

Technology:

- Redis (current)
- Kafka (future)

### Detection Layer

Responsibilities:

- Rule detection
- Statistical detection
- Future ML detection

Detection must work without LLMs.

### Correlation Layer

Responsibilities:

- Determine relationships between events
- Build service impact chains
- Find probable causes

### Incident Memory

Responsibilities:

- Store incidents
- Store fixes
- Store runbooks
- Similarity search

### Agent Layer

Contains:

- Log Agent
- Metric Agent
- Knowledge Agent
- Correlation Agent
- Remediation Agent

### Coordinator Agent

Combines all agent outputs.

Responsible for final reasoning.

### Decision Engine

Converts reasoning into actions.

### Action Engine

Executes approved actions.

### Verification Engine

Validates if actions worked.

### Learning Layer

Stores outcomes for future investigations.