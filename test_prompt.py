from services.ai.prompts import build_incident_prompt

sample_log = {
    "service": "payment-service",
    "message": "Database timeout",
    "anomaly_score": 0.91,
    "detection_metadata": {
        "flags": [
            "REPEATED_FAILURE",
            "HIGH_ANOMALY_RATIO"
        ]
    }
}

print(build_incident_prompt(sample_log))