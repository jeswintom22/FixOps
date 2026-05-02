from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List,Optional

app = FastAPI()

class Log(BaseModel):
    timestamp:Optional[str]=None
    level:str="INFO"
    service:str="unknown"
    message:str
    trace_id:Optional[str]=None
    metadata:Optional[dict]= Field(default_factory=dict)

class LogRequest(BaseModel):
    logs:List[Log]

@app.post("/test")
async def test_schema(payload:LogRequest):
    return payload