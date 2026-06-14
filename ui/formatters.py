from __future__ import annotations

import re


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
