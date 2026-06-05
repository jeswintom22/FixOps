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
Return ONLY valid JSON.

Do not include markdown.
Do not include explanations.
Do not wrap JSON in code blocks.

Provide your response strictly in JSON format:

{{
    "root_cause": "...",
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "suggested_fix": "..."
}}
"""