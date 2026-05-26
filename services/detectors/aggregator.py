def aggregate_detection(*results) -> dict:              # combines detector outputs
    total_score = 0
    triggered_detectors = []
    all_flags=[]

    for result in results:
        total_score += result["score"]
        all_flags.extend(result["flags"])
        if result["triggered"]:
            triggered_detectors.append(
                result["detector"]
            )
       
    average_score = (
        total_score/len(results)
    )
    average_score=round(average_score,2)
    return{
        "event_type":( 
            "anomaly" 
            if average_score>=0.3
            else "normal"
        ),
        "anomaly_score": average_score,
        "detection_metadata": {
            "flags": all_flags,
            "detectors_triggered": triggered_detectors
        }
    }