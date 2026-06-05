def build_incident_prompt(log):

    return f"""
You are an expert DevOps incident analyst.

Analyze the following anomaly.

Service:
{log["service"]}

Log Message:
{log["message"]}

Anomaly Score:
{log["anomaly_score"]}

Detection Flags:
{log.get("detection_metadata", {}).get("flags", [])}

Provide your response strictly in JSON format:

{{
    "root_cause": "...",
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "suggested_fix": "..."
}}
"""