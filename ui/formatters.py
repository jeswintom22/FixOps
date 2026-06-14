from __future__ import annotations

import re
from typing import Any

TRACE_STEPS: list[tuple[str, str]] = [
    ("LOG_ANALYSIS", "Log Analysis"),
    ("KNOWLEDGE_RETRIEVAL", "Knowledge Retrieval"),
    ("ROOT_CAUSE_ANALYSIS", "Root Cause Analysis"),
    ("REMEDIATION", "Remediation Planning"),
    ("REPORT_GENERATION", "Report Generation"),
]


def parse_remediation_steps(section: str) -> list[str]:
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    if not lines:
        return []

    steps: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^\s*(?:\d+[\).\:-]|[-*])\s*", "", line).strip()
        if cleaned:
            steps.append(cleaned)

    return steps or [section.strip()]


def parse_evidence_items(section: str) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", section.strip()) if chunk.strip()]
    if chunks:
        return chunks

    lines = [line.strip(" -") for line in section.splitlines() if line.strip()]
    return lines or [section.strip()]


def infer_retry_flags(report: dict[str, Any]) -> tuple[bool, bool]:
    root_cause_section = str(report.get("root_cause_section", "")).lower()
    remediation_section = str(report.get("remediation_section", ""))
    root_cause_retried = "retry" in root_cause_section or "expanded" in root_cause_section
    remediation_retried = count_sentences(remediation_section) < 3
    return root_cause_retried, remediation_retried


def build_reasoning_trace(
    incident: dict[str, Any],
    investigation: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, Any]:
    root_cause_retried, remediation_retried = infer_retry_flags(report)
    investigation_status = str(investigation.get("status", "")).upper()
    current_step = investigation.get("current_step")
    step_positions = {code: index for index, (code, _) in enumerate(TRACE_STEPS)}
    current_index = step_positions.get(current_step, -1)

    timeline: list[dict[str, str]] = []
    for index, (code, label) in enumerate(TRACE_STEPS):
        status = "completed" if investigation_status == "COMPLETED" else "skipped"
        if investigation_status != "COMPLETED" and index <= current_index:
            status = "completed"
        if code == "ROOT_CAUSE_ANALYSIS" and root_cause_retried:
            status = "retried"
        if code == "REMEDIATION" and remediation_retried:
            status = "retried"
        timeline.append({"code": code, "label": label, "status": status})

    severity = str(incident.get("severity", "MEDIUM")).upper()
    retrieval_depth = "top_k=8" if severity in {"CRITICAL", "HIGH"} else "top_k=3"
    retrieval_label = "full knowledge retrieval" if retrieval_depth == "top_k=8" else "lighter knowledge retrieval"

    explanations = [
        f"Severity {severity} led the agent to choose {retrieval_label} ({retrieval_depth}).",
        (
            "The root cause narrative suggests the agent retried with expanded context before finalizing the hypothesis."
            if root_cause_retried
            else "The final root cause section does not suggest a low-confidence retry."
        ),
        (
            "The remediation section is short enough to trigger the UI's thin-plan retry heuristic."
            if remediation_retried
            else "The remediation section looks substantial enough that the UI does not flag a retry heuristic."
        ),
    ]

    return {
        "timeline": timeline,
        "root_cause_retried": root_cause_retried,
        "remediation_retried": remediation_retried,
        "explanations": explanations,
    }


def count_sentences(section: str) -> int:
    sentences = [segment.strip() for segment in re.split(r"[.!?]+", section) if segment.strip()]
    return len(sentences)


def build_report_markdown(report: dict[str, str]) -> str:
    return "\n\n".join(
        [
            f"# {report.get('title', 'FixOps IQ Report')}",
            "## Executive Summary",
            report.get("executive_summary", "Not available."),
            "## Incident Summary",
            report.get("incident_summary", "Not available."),
            "## Root Cause Analysis",
            report.get("root_cause_section", "Not available."),
            "## Supporting Evidence",
            report.get("evidence_section", "Not available."),
            "## Remediation Plan",
            report.get("remediation_section", "Not available."),
        ]
    )
