# Context Engineering Architecture

FixOps uses Context Engineering rather than prompt engineering.

---

## Goal

Provide the right information to the right agent.

Do not dump raw data into a model.

---

## Context Sources

- Logs
- Metrics
- Traces
- Deployments
- Incident Memory
- Runbooks
- Previous Actions
- Verification Results

---

## Context Providers

context/providers/

- log_provider.py
- metric_provider.py
- memory_provider.py
- deployment_provider.py
- trace_provider.py

---

## Context Builder

Creates a unified IncidentContext.

Example:

IncidentContext

- incident
- logs
- metrics
- deployments
- related_incidents
- runbooks
- dependencies

---

## Context Flow

Incident
↓
Context Providers
↓
Context Builder
↓
Agent
↓
Coordinator

---

## Rule

Agents receive only the context relevant to their role.