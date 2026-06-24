# Architecture Decision Records

## ADR-001

Decision:
Detection remains independent from LLM.

Reason:
System must function if models fail.

Status:
Accepted

---

## ADR-002

Decision:
Redis is the primary queue.

Reason:
Current scale does not require Kafka.

Status:
Accepted

---

## ADR-003

Decision:
Provider abstraction is mandatory.

Reason:
Avoid vendor lock-in.

Status:
Accepted

---

## ADR-004

Decision:
Incident memory will use PostgreSQL and pgvector.

Reason:
Similarity search is required.

Status:
Accepted

---

## ADR-005

Decision:
Coordinator Agent is the only component allowed to generate final recommendations.

Reason:
Centralized decision making.

Status:
Accepted

---

## ADR-006

Decision:

FixOps uses Context Engineering.

Reason:

Agents should receive curated context rather than raw system data.

Implementation:

Context Providers
→ Context Builder
→ IncidentContext
→ Agent Context Slices
→ Coordinator

Status:

Accepted

---

## ADR-007

Decision:
Context generation uses ContextProvider and ContextBuilder.

Reason:
Decouple context assembly from storage and retrieval systems.

Implementation:

ContextProvider
↓
ContextBuilder
↓
IncidentContext

Status:
Accepted
