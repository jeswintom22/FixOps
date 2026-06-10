from services.actions.decision_engine import decide_action
from services.actions.alert_service import send_alert
from database import save_action
from services.actions.safe_actions import (
    restart_service,
    clear_cache
)


def process_action(analysis):

    decision = decide_action(analysis)

    save_action(
        trace_id=analysis.get("trace_id"),
        service=analysis.get("service"),
        severity=analysis.get("severity"),
        action_type=decision["action_type"]
    )

    if decision["action_type"] == "alert":
        send_alert(analysis, decision)
        
    if decision["action_type"] == "auto_remediation":
        service_name = analysis.get(
            "service",
            "unknown-service"
        )

        restart_service(service_name)

    return decision