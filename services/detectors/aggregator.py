def aggregate_detection(*results) -> dict:
    total_score = 0
    triggered = False
    all_flags=[]

    for result in results:
        total_score+=result["score"]

        if result["triggered"]:
            triggered= True
        all_flags.extend(result["flags"])
    average_score = total_score/len(results)
    return{
        "event_type": "anomaly" if triggered else "normal",
        "anomaly_score": round(average_score, 2),
        "detection_metadata": {
            "flags": all_flags,
            "detectors_triggered": [
                r["detector"]
                for r in results
                if r["triggered"]
            ]
        }
    }