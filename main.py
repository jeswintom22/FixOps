from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List,Optional
import uuid
from datetime import datetime

app = FastAPI()
logs_db =[]

def ingestion_service(logs):   #ingestion service(logic layer)
    processed_logs=[]

    for log in logs:
        log_dict=log.dict()
        if not log_dict.get("trace_id"):      #attach trace_id
            log_dict["trace_id"]=str(uuid.uuid4())
        
        if not log_dict.get("timestamp"):    #normalize timestamp
            log_dict["timestamp"]=datetime.utcnow().isoformat()
        processed_logs.append(log_dict)
    logs_db.extend(processed_logs)
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

@app.get("/logs")                    #debug point
def get_logs():
    return {
        "total":len(logs_db),
        "logs":logs_db
    }

@app.post("/ingest")                               #real ingestion endpoint
async def ingest_logs(payload: LogRequest):
    processed = ingestion_service(payload.logs)

    return {
        "status":"ingested",
        "count":len(processed),
        "logs":processed
    }
