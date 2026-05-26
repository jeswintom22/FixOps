FAILURE_KEYWORDS = [
    "failed",
    "exception",
    "timeout",
    "refused",
    "crash",
    "unreachable"
]
def rule_detector(log:dict) -> dict:                       #deterministic anomaly rules
    score = 0.0
    flags=[]
    triggered = False
    message = log.get("message","").lower()

    level =log.get("level","INFO")

    metadata = log.get("metadata",{})
    
    #RULE 1 - ERROR level
    if level =="ERROR":
        triggered =True
        score += 0.4
        flags.append("ERROR_LEVEL")
    
    # RULE 2 - Faliur keywords
    for keyword in FAILURE_KEYWORDS:

        if keyword in message:
            triggered = True
            score +=0.2

            flags.append(f"KEYWORD_{keyword.upper()}")
    
    #RULE 3 - High Response Time
    response_time = metadata.get(
        "response_time",
        0
    )

    if response_time > 2000:
        triggered =True
        score +=0.3
        flags.append("HIGH_RESPONSE_TIME")
    
    #prevent runaway scores
    score = min(score,1.0)

    return{
        "detector": "rule_detector",
        "triggered": triggered,
        "score": round(score,2),
        "flags": flags
    }