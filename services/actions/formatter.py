def build_alert_message(
    analysis,
    decision
):
    return f"""
========== ALERT ==========

Severity: {analysis.get('severity')}

Service: {analysis.get('service')}

Trace ID: {analysis.get('trace_id')}

Root Cause:
{analysis.get('root_cause')}

Suggested Fix:
{analysis.get('suggested_fix')}

Action:
{decision.get('action_type')}

Priority:
{decision.get('priority')}

===========================
"""