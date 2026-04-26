from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message":"API is working"}
@app.post("/ingest")
async def ingest_logs(payload:dict):
    logs = payload.get("logs",[])
    return{
        "status":"received",
        "count":len(logs),
        "logs":logs 
    }