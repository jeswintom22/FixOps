from services.ai.llm_service import analyze_incident
from legacy.database import save_analysis


def process_analysis(log):

    result = analyze_incident(log)

    save_analysis(
        trace_id=log["trace_id"],
        service=log["service"],
        anomaly_score=log["anomaly_score"],
        severity=result.get("severity"),
        root_cause=result.get("root_cause"),
        suggested_fix=result.get("suggested_fix")
    )

    return result