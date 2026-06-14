from __future__ import annotations

from typing import Any

import streamlit as st

from ui.api import FixOpsApiError, create_incident, get_report, run_investigation
from ui.config import API_URL_ENV_VAR, get_api_base_url
from ui.formatters import build_report_markdown, parse_evidence_items, parse_remediation_steps


st.set_page_config(
    page_title="FixOps IQ",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


WORKFLOW_STEPS = [
    "Incident",
    "Log Analysis",
    "Knowledge Retrieval",
    "Root Cause Analysis",
    "Remediation Planning",
    "Report Generation",
]
SEVERITY_OPTIONS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
DEFAULT_LOG = """2026-06-12T14:22:11Z ERROR payments-api request timed out after 30s
2026-06-12T14:22:13Z WARN payments-api retry budget exhausted for gateway dependency
2026-06-12T14:22:18Z ERROR payments-api downstream 503 returned by card processor
"""


def initialize_state() -> None:
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("incident", None)
    st.session_state.setdefault("investigation", None)
    st.session_state.setdefault("error_message", None)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: #f5f7fb;
            }
            .block-container {
                max-width: 1440px;
                padding-top: 2rem;
                padding-bottom: 2rem;
            }
            .fixops-header {
                background: white;
                border: 1px solid #d9e2ec;
                border-radius: 16px;
                padding: 1.5rem 1.75rem;
                margin-bottom: 1rem;
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
            }
            .fixops-kicker {
                color: #486581;
                font-size: 0.9rem;
                font-weight: 600;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }
            .fixops-title {
                color: #102a43;
                font-size: 2.2rem;
                font-weight: 700;
                margin: 0;
            }
            .fixops-subtitle {
                color: #627d98;
                font-size: 1rem;
                margin-top: 0.35rem;
            }
            .workflow-card {
                background: white;
                border: 1px solid #d9e2ec;
                border-radius: 16px;
                padding: 1rem 1.25rem;
                margin-bottom: 1.25rem;
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
            }
            .workflow-title {
                color: #102a43;
                font-size: 0.95rem;
                font-weight: 600;
                margin-bottom: 0.75rem;
            }
            .workflow-row {
                color: #243b53;
                font-size: 0.95rem;
                line-height: 1.6;
                word-break: break-word;
            }
            .metric-strip {
                display: flex;
                gap: 0.75rem;
                flex-wrap: wrap;
                margin-bottom: 1rem;
            }
            .metric-tile {
                background: #f8fafc;
                border: 1px solid #d9e2ec;
                border-radius: 12px;
                padding: 0.85rem 1rem;
                min-width: 180px;
            }
            .metric-label {
                color: #627d98;
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin-bottom: 0.25rem;
            }
            .metric-value {
                color: #102a43;
                font-size: 1rem;
                font-weight: 700;
            }
            div[data-testid="stForm"] {
                border: none;
                padding: 0;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: white;
                border-radius: 16px;
                border: 1px solid #d9e2ec;
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
            }
            div[data-testid="stExpander"] {
                border: 1px solid #d9e2ec;
                border-radius: 12px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="fixops-header">
            <div class="fixops-kicker">Enterprise Incident Intelligence</div>
            <h1 class="fixops-title">FixOps IQ</h1>
            <div class="fixops-subtitle">Enterprise AI SRE Agent</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow() -> None:
    workflow = " &rarr; ".join(WORKFLOW_STEPS)
    st.markdown(
        f"""
        <div class="workflow-card">
            <div class="workflow-title">Investigation Workflow</div>
            <div class="workflow-row">{workflow}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def submit_incident(title: str, description: str, raw_log: str, severity: str) -> None:
    payload = {
        "title": title,
        "description": description or None,
        "raw_log": raw_log,
        "severity": severity,
    }

    with st.spinner("Creating incident and running investigation..."):
        incident = create_incident(payload)
        investigation = run_investigation(incident["id"])
        report_id = investigation.get("report_id")
        if not report_id:
            raise FixOpsApiError("Investigation completed without a generated report ID.")
        report = get_report(report_id)

    st.session_state["incident"] = incident
    st.session_state["investigation"] = investigation["investigation"]
    st.session_state["report"] = report
    st.session_state["error_message"] = None


def render_submission_panel() -> None:
    with st.container(border=True):
        st.subheader("Incident Submission")
        st.caption(f"API endpoint: `{get_api_base_url()}` from `${API_URL_ENV_VAR}`")

        with st.form("incident_submission_form", clear_on_submit=False):
            title = st.text_input(
                "Title",
                placeholder="Payments API timeout across primary region",
            )
            description = st.text_area(
                "Description",
                placeholder="Describe user impact, affected systems, and any immediate context.",
                height=110,
            )
            raw_log = st.text_area(
                "Raw Log",
                value=DEFAULT_LOG,
                height=260,
            )
            severity = st.selectbox("Severity", options=SEVERITY_OPTIONS, index=2)
            submitted = st.form_submit_button(
                "Investigate Incident",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not title.strip() or not raw_log.strip():
                st.session_state["error_message"] = "Title and Raw Log are required."
            else:
                try:
                    submit_incident(title.strip(), description.strip(), raw_log.strip(), severity)
                except FixOpsApiError as exc:
                    st.session_state["error_message"] = str(exc)

        if st.session_state.get("error_message"):
            st.error(st.session_state["error_message"])


def render_result_metrics(incident: dict[str, Any], investigation: dict[str, Any], report: dict[str, Any]) -> None:
    st.markdown(
        f"""
        <div class="metric-strip">
            <div class="metric-tile">
                <div class="metric-label">Severity</div>
                <div class="metric-value">{incident.get("severity", "n/a")}</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">Incident Status</div>
                <div class="metric-value">{incident.get("status", "n/a")}</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">Investigation Status</div>
                <div class="metric-value">{investigation.get("status", "n/a")}</div>
            </div>
            <div class="metric-tile">
                <div class="metric-label">Report Version</div>
                <div class="metric-value">{report.get("format_version", "1.0")}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results_panel() -> None:
    with st.container(border=True):
        st.subheader("Investigation Results")

        report = st.session_state.get("report")
        incident = st.session_state.get("incident")
        investigation = st.session_state.get("investigation")

        if not report or not incident or not investigation:
            st.info("Submit an incident to generate a complete SRE investigation report.")
            return

        render_result_metrics(incident, investigation, report)

        st.markdown("#### Executive Summary")
        st.write(report.get("executive_summary", "Not available."))

        st.markdown("#### Root Cause Analysis")
        st.write(report.get("root_cause_section", "Not available."))

        st.markdown("#### Supporting Evidence")
        evidence_items = parse_evidence_items(report.get("evidence_section", ""))
        for index, item in enumerate(evidence_items, start=1):
            with st.expander(f"Evidence {index}", expanded=index == 1):
                st.write(item)

        st.markdown("#### Remediation Plan")
        remediation_steps = parse_remediation_steps(report.get("remediation_section", ""))
        if remediation_steps:
            st.markdown("\n".join(f"{index}. {step}" for index, step in enumerate(remediation_steps, start=1)))
        else:
            st.write("No remediation plan available.")

        st.markdown("#### Final Report")
        st.markdown(build_report_markdown(report))

        with st.expander("Report Metadata"):
            st.json(
                {
                    "incident_id": report.get("incident_id"),
                    "investigation_id": report.get("investigation_id"),
                    "report_id": report.get("id"),
                    "generated_at": report.get("generated_at"),
                }
            )


def main() -> None:
    initialize_state()
    inject_styles()
    render_header()
    render_workflow()

    left_column, right_column = st.columns([1, 1.35], gap="large")

    with left_column:
        render_submission_panel()

    with right_column:
        render_results_panel()


if __name__ == "__main__":
    main()
