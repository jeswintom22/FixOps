from state.counters import (
    service_request_counts,
    service_anomaly_counts,
    message_frequency,
    service_recent_logs
)


def statistical_detector(log: dict):

    score = 0.0
    flags = []
    triggered = False

    message = log.get("message", "")
    service = log.get("service")

    # ----------------------------------
    # Repeated Failure Detection
    # ----------------------------------

    if message_frequency[message] >= 5:

        triggered = True
        score += 0.3

        flags.append(
            "REPEATED_FAILURE"
        )

    # ----------------------------------
    # High Anomaly Ratio Detection
    # ----------------------------------

    requests = service_request_counts[service]
    anomalies = service_anomaly_counts[service]

    if requests > 0:

        ratio = anomalies / requests

        if ratio > 0.3:

            triggered = True
            score += 0.3

            flags.append(
                "HIGH_ANOMALY_RATIO"
            )

    # ----------------------------------
    # Anomaly Burst Detection
    # ----------------------------------

    recent_logs = service_recent_logs[service]

    recent_anomalies = 0

    for item in recent_logs:

        if item.get("event_type") == "anomaly":
            recent_anomalies += 1

    if recent_anomalies >= 10:

        triggered = True
        score += 0.4

        flags.append(
            "ANOMALY_BURST"
        )

    return {
        "detector": "statistical_detector",
        "triggered": triggered,
        "score": round(score, 2),
        "flags": flags
    }