from services.actions.decision_engine import decide_action
from services.actions.alert_service import send_alert


def process_action(analysis):

    decision = decide_action(analysis)

    if decision["action_type"] == "alert":
        send_alert(analysis, decision)

    return decision