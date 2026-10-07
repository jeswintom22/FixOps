from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

from ui.api import (
    FixOpsApiError,
    create_incident,
    get_investigation,
    get_investigation_report,
    run_investigation,
)
from ui.config import API_KEY_ENV_VAR, API_URL_ENV_VAR, get_api_base_url

st.set_page_config(page_title="FixOps", page_icon="🔧", layout="wide")

DEFAULT_LOG = """2026-06-12T14:22:11Z ERROR payments-api request timed out after 30s
2026-06-12T14:22:13Z WARN payments-api retry budget exhausted for gateway dependency
2026-06-12T14:22:18Z ERROR payments-api downstream 503 returned by card processor
"""


def init_state() -> None:
    for key in ("report", "incident", "investigation", "error"):
        st.session_state.setdefault(key, None)


def render_header() -> None:
    st.title("FixOps")
    st.caption("AI SRE agent for incident investigation")
    api_key_status = "set" if os.getenv(API_KEY_ENV_VAR) else "not set"
    st.markdown(
        f"Backend: `{get_api_base_url()}` (from `${API_URL_ENV_VAR}`). "
        f"API key: `{api_key_status}` (from `${API_KEY_ENV_VAR}`)."
    )


def submit_incident(title: str, description: str, raw_log: str, severity: str) -> None:
    payload = {
        "title": title,
        "description": description or None,
        "raw_log": raw_log,
        "severity": severity,
    }

    with st.spinner("Creating incident and queueing investigation..."):
        incident = create_incident(payload)
        investigation = run_investigation(incident["id"])

        investigation_data = investigation["investigation"]
        for _ in range(120):
            if investigation_data.get("status") in {"COMPLETED", "FAILED"}:
                break
            import time

            time.sleep(1)
            investigation_data = get_investigation(investigation_data["id"])

        if investigation_data.get("status") != "COMPLETED":
            error = investigation_data.get("error_message") or "Investigation did not complete."
            raise FixOpsApiError(error)

        report = get_investigation_report(investigation_data["id"])

    st.session_state["incident"] = incident
    st.session_state["investigation"] = investigation_data
    st.session_state["report"] = report
    st.session_state["error"] = None


def render_input_panel() -> None:
    with st.container(border=True):
        st.subheader("Submit incident")

        with st.form("incident_form", clear_on_submit=False):
            title = st.text_input("Title", placeholder="Payments API timeout across primary region")
            description = st.text_area("Description", height=80)
            raw_log = st.text_area("Raw log", value=DEFAULT_LOG, height=200)
            severity = st.selectbox(
                "Severity", options=["CRITICAL", "HIGH", "MEDIUM", "LOW"], index=2
            )
            submitted = st.form_submit_button("Investigate", type="primary")

        if submitted:
            if not title.strip() or not raw_log.strip():
                st.session_state["error"] = "Title and raw log are required."
            else:
                try:
                    submit_incident(title.strip(), description.strip(), raw_log.strip(), severity)
                except FixOpsApiError as exc:
                    st.session_state["error"] = str(exc)

        if st.session_state.get("error"):
            st.error(st.session_state["error"])


def render_results_panel() -> None:
    report = st.session_state.get("report")
    incident = st.session_state.get("incident")
    investigation = st.session_state.get("investigation")

    with st.container(border=True):
        st.subheader("Investigation report")

        if not report or not incident or not investigation:
            st.info("Submit an incident to generate a report.")
            return

        st.markdown(f"**Incident:** {incident.get('title')}")
        st.markdown(f"**Severity:** `{incident.get('severity')}`")
        st.markdown(f"**Status:** `{incident.get('status')}`")
        st.markdown(f"**Confidence:** `{report.get('confidence_score', 'n/a')}`")

        st.markdown("### Executive summary")
        st.write(report.get("executive_summary", "Not available."))

        st.markdown("### Root cause")
        st.write(report.get("root_cause_section", "Not available."))

        st.markdown("### Evidence")
        for index, item in enumerate(report.get("evidence_refs", []), start=1):
            with st.expander(
                f"Evidence {index}: {item.get('source_type', 'unknown')}", expanded=index == 1
            ):
                st.markdown(f"**Source:** `{item.get('source_ref')}`")
                st.write(item.get("content", "No content"))

        st.markdown("### Remediation plan")
        for step in report.get("remediation_steps", []):
            risk = step.get("risk_level", "LOW")
            color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(risk, "gray")
            st.markdown(f"**{step.get('order')}.** {step.get('action')}")
            st.markdown(f":{color}[Risk: `{risk}`]")
            if step.get("rationale"):
                st.caption(step["rationale"])
            if step.get("command_hint"):
                st.code(step["command_hint"], language="bash")

        if investigation.get("root_cause_retried"):
            st.caption("Root cause analysis was retried with expanded context.")
        if investigation.get("remediation_retried"):
            st.caption("Remediation planning was retried.")


def main() -> None:
    init_state()
    render_header()

    left, right = st.columns([1, 1.5])
    with left:
        render_input_panel()
    with right:
        render_results_panel()


if __name__ == "__main__":
    main()
