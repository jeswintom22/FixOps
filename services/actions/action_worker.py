from services.actions.decision_engine import decide_action


def process_action(analysis):
    print("Processing action")

    decision = decide_action(analysis)

    print("Analysis:")
    print(analysis)

    print("Decision:")
    print(decision)

    return decision