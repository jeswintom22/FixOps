import uuid
from datetime import datetime

logs_db=[]                #temporarary 

def process_log(log_dict):         
    if not log_dict.get("trace_id"):          #ATTACH TRACE_ID
        log_dict["trace_id"]=str(uuid.uuid4())
    
    if not log_dict.get("timestamp"):          #NORMALIZE TIMESTAMP
        log_dict["timestamp"]=datetime.utcnow().isoformat()
    
    log_dict["level"]=log_dict["level"].upper()    #NORMALIZE LEVEL

    logs_db.append(log_dict)
    return log_dict
