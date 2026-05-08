import uuid
from datetime import datetime
from database import save_log



def process_log(log_dict):            #PROCESS LOG AND STORE IN DB
    
    normalized_log=normalize_log(log_dict)
    
    analyzed_log = detect_anomaly(normalized_log)

    save_log(analyzed_log)
    return analyzed_log

def normalize_log(log_dict):            #NORMALIZE LOG WITHOUT STORING IN DB

    if not log_dict.get("timestamp"):       #NORMALIZE TIMESTAMP
        log_dict["timestamp"]=datetime.utcnow().isoformat()
    
    log_dict["level"]=log_dict["level"].upper()     #NORMALIZE LEVEL

    if not log_dict.get("service"):                   #Service fallback
        log_dict["service"]="unknown"
    
    if not log_dict.get("metadata"):                 #metadata fallback
        log_dict["metadata"]={}
    
    if not log_dict.get("trace_id"):                #trace_id generation
        log_dict["trace_id"]=str(uuid.uuid4())
    
    return log_dict

def detect_anomaly(log_dict):                     #Detection Function

    if log_dict["level"]=="ERROR":
        log_dict["event_type"]="anomaly"
        log_dict["anomaly_score"] = 1
    else:
        log_dict["event_type"]="normal"
        log_dict["anomaly_score"]=0
    return log_dict