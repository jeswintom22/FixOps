from datetime import datetime
import uuid

def normalize_log(log: dict) -> dict:
    log["timestamp"]=(
        log.get("timestamp")
        or datetime.utcnow().isoformat()
    )
    log["level"]=(
        log.get("level","INFO".upper())
    )
    log["service"]=(
        log.get("service","unknown-service")
    )
    log["metadata"]=(
        log.get("metadata",{})
    )
    log["trace_id"]=(
        log.get("trace_id")
        or str(uuid.uuid4())
    )
    return log