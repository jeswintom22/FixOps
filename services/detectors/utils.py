from state.counters import(
    service_anomaly_counts,
    service_request_counts
    message_frequency,
    service_recent_logs
)

def update_counters(log:dict):

    service = log.get("service")
    message = log.dict("message")
    event_type = log.get("event_type")

    service_request_counts[service] +=1

    message_frequency[message] +=1

    if event_type == "anomaly":
        service_anomaly_counts[service] +=1

    service_recent_logs[service].append(log)