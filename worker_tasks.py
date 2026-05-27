from services.normalizer import normalize_log

from services.detectors.rule_detector import(
    rule_detector
)

from services.detectors.statistical_detector import(
    statistical_detector
)

from services.detectors.aggregator import(
    aggregate_detection
)


from database import save_log





def process_log(log:dict):           
    
    normalized_log=normalize_log(log)
    
    rule_result = rule_detector(normalized_log)

    statistical_result = statistical_detector(normalized_log)

    final_detection = aggregate_detection(
        rule_result,
        statistical_result
    )

    normalized_log.update(final_detection)

    save_log(normalized_log)
    
    return normalized_log

