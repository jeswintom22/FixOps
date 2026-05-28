from state.counters import (
    service_request_counts,
    service_anomaly_counts,
    message_frequency,
    service_recent_logs
)


def update_counters(log: dict):

    service = log.get("service")

    message = log.get("message")

    event_type = log.get("event_type")

    # total requests
    service_request_counts[service] += 1

    # repeated messages
    message_frequency[message] += 1

    # anomaly counts
    if event_type == "anomaly":
        service_anomaly_counts[service] += 1

    # recent logs
    service_recent_logs[service].append(log)

    # debug output
    print("Service Requests:")
    print(dict(service_request_counts))

    print("Message Frequency:")
    print(dict(message_frequency))