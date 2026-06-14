import redis
from rq import Queue

redis_conn = redis.Redis(
    host="localhost",
    port=6379
)

# Existing queue
log_queue = Queue(
    "logs",
    connection=redis_conn
)

# NEW: Week 3 AI queue
analysis_queue = Queue(
    "analysis",
    connection=redis_conn
)

action_queue = Queue(
    "actions",
    connection=redis_conn
)