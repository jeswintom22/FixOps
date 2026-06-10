def decide_action(analysis):
    severity = analysis.get("severity", "LOW")

    if severity == "LOW":
        return {
            "action_type": "store",
            "priority": "low"
        }

    if severity == "MEDIUM":
        return {
            "action_type": "alert",
            "priority": "medium"
        }

    if severity == "HIGH":
        return {
            "action_type": "alert",
            "priority": "high",
            "webhook": True
        }

    if severity == "CRITICAL":
        return {
            "action_type": "auto_remediation",
            "priority": "critical",
            "webhook":True
        }

    return {
        "action_type": "store",
        "priority": "low"
    }