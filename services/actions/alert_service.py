from services.actions.formatter import (
    build_alert_message
)


def send_alert(
    analysis,
    decision
):
    message = build_alert_message(
        analysis,
        decision
    )

    print(message)