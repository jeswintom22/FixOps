# Incident Memory Package

## Objective

Implement the Incident Memory Layer for FixOps v2.

This layer stores historical incidents, investigations, fixes, and outcomes.

It provides similarity search and historical context to agents.

This is Layer 6 of the architecture.

---

## Why This Exists

The current FixOps MVP analyzes incidents independently.

The system cannot learn from previous incidents.

Incident Memory allows:

- Similar incident retrieval
- Historical fix retrieval
- Runbook retrieval
- Operational learning

---

## Architecture Position

Signal Sources
↓
Ingestion
↓
Queue
↓
Detection
↓
Correlation
↓
INCIDENT MEMORY ← THIS PACKAGE
↓
Agents
↓
Coordinator
↓
Decision
↓
Action
↓
Verification
↓
Learning

---

## Existing Components

Already implemented:

- Detection Engine
- LLM Analysis
- Decision Engine
- Action Engine
- Action History

Do not modify these systems.

Extend the architecture.

---

## Constraints

Must:

- Use PostgreSQL
- Use pgvector
- Support semantic similarity search
- Remain provider independent
- Remain asynchronous

Must Not:

- Modify Detection Layer
- Modify Decision Engine
- Modify Action Engine

---

## Required Components

### Models

Incident

KnowledgeEntry

Runbook

IncidentEmbedding

---

### Repositories

IncidentRepository

KnowledgeRepository

RunbookRepository

---

### Services

EmbeddingService

SimilaritySearchService

IncidentMemoryService

---

### Context Providers

memory_provider.py

---

## API Requirements

GET /incidents

GET /incidents/{id}

GET /incidents/similar/{id}

---

## Acceptance Criteria

System can:

1. Store incidents

2. Generate embeddings

3. Store embeddings

4. Retrieve similar incidents

5. Return top-k results

6. Supply memory context to agents

---

## Out Of Scope

- Multi-Agent System
- Correlation Layer
- Verification Engine
- Learning Layer