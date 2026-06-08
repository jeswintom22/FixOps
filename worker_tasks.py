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

from services.detectors.utils import(
    update_counters
)

from database import save_log

from queue_config import (
    log_queue,
    analysis_queue,
    action_queue
)

from services.ai.analysis_worker import (
    process_analysis
)



def process_log(log: dict):

    normalized_log = normalize_log(log)

    rule_result = rule_detector(normalized_log)

    statistical_result = statistical_detector(normalized_log)

    final_detection = aggregate_detection(
        rule_result,
        statistical_result
    )

    normalized_log.update(final_detection)

    update_counters(normalized_log)

    save_log(normalized_log)

    # Week 3 Step 2
    if normalized_log["event_type"] == "anomaly":
        analysis_queue.enqueue(
            process_analysis,
            normalized_log
        )

    return normalized_log
