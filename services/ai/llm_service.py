from services.ai.prompts import build_incident_prompt

from services.ai.llm_factory import get_provider


def analyze_incident(log):

    prompt = build_incident_prompt(log)

    provider = get_provider()

    response = provider.analyze(prompt)

    return response