from collections import defaultdict,deque

service_request_counts = defaultdict(int)

service_anomaly_counts =defaultdict(int)

message_frequeny = defaultdict(int)

service_recent_logs = defaultdict(
    lambda:deque(maxlen=20)
)