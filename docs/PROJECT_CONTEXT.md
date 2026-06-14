# FixOps IQ – Enterprise AI SRE Agent

## Hackathon

Microsoft Agents League 2026

Track:
Reasoning Agents

## Problem

Operations teams spend significant time investigating incidents, searching documentation, identifying root causes, and determining remediation steps.

This process is often manual, slow, and dependent on institutional knowledge.

## Solution

FixOps IQ is an AI-powered reasoning agent that:

1. Accepts an incident or error log
2. Analyzes the incident
3. Retrieves relevant operational knowledge
4. Identifies root causes
5. Generates remediation recommendations
6. Produces an investigation report

## Existing Stack

* Python
* FastAPI
* PostgreSQL
* Redis
* Docker

## Existing Features

* Incident management
* Log analysis
* Root cause investigation
* Background job processing

## Hackathon Features

* Multi-step reasoning workflow
* Knowledge retrieval layer
* Azure AI Foundry integration
* Structured investigation reports

## Workflow

Incident
↓
Log Analysis
↓
Knowledge Retrieval
↓
Root Cause Analysis
↓
Remediation Planning
↓
Investigation Report

## Core API

POST /incidents

POST /investigate

GET /incidents/{id}

GET /reports/{id}

## Success Criteria

Input:
Database connection timeout error

Output:

* Incident summary
* Root cause analysis
* Supporting evidence
* Remediation recommendations
* Investigation report
