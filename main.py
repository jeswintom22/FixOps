from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List,Optional
import uuid
from datetime import datetime
from queue_config import log_queue
from database import cursor
import json
from worker_tasks import process_log

app = FastAPI()

def ingestion_service(logs):   #ingestion service(logic layer)
    processed_logs=[]

    for log in logs:
        log_dict=log.dict()
        if not log_dict.get("trace_id"):      #attach trace_id
            log_dict["trace_id"]=str(uuid.uuid4())
        
        if not log_dict.get("timestamp"):    #normalize timestamp
            log_dict["timestamp"]=datetime.utcnow().isoformat()
        processed_logs.append(log_dict)
    
    return processed_logs
class Log(BaseModel):
    timestamp:Optional[str]=None
    level:str="INFO"
    service:str="unknown"
    message:str
    trace_id:Optional[str]=None
    metadata:Optional[dict]= Field(default_factory=dict)

class LogRequest(BaseModel):
    logs:List[Log]

@app.get("/logs")
def get_logs():

    cursor.execute("SELECT * FROM logs")

    rows = cursor.fetchall()

    logs = []

    for row in rows:
        logs.append({
            "id": row[0],
            "timestamp": row[1],
            "level": row[2],
            "service": row[3],
            "message": row[4],
            "trace_id": row[5],
            "metadata": json.loads(row[6]),
            "event_type": row[7],
            "anomaly_score": row[8]
        })

    return {
        "total": len(logs),
        "logs": logs
    }

@app.post("/ingest")                               #real ingestion endpoint
async def ingest_logs(payload: LogRequest):
    for log in payload.logs:
        log_queue.enqueue(process_log,log.dict())

    return {
        "status":"queued",
        "count":len(payload.logs)
    }
