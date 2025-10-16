# orchestrator.py
from typing import Dict
from loguru import logger

from agents import PlannerAgent, WeatherAgent, LocationAgent, SynthesizerAgent, BaseAgent

AGENT_REGISTRY = {
    "PlannerAgent": PlannerAgent,
    "WeatherAgent": WeatherAgent,
    "LocationAgent": LocationAgent,
    "SynthesizerAgent": SynthesizerAgent,
}

def _create_agent(agent_or_cls):
    """Ensure we always have an instance, even if the registry accidentally stores a class."""
    try:
        if isinstance(agent_or_cls, type):
            return agent_or_cls()
        return agent_or_cls
    except Exception as e:
        raise RuntimeError(f"Failed to create agent from {agent_or_cls}: {e}")

def run_orchestration(user_input: str) -> str:
    # 1) Plan (Planner sees only the agents that can appear in the plan)
    plan_catalog = [WeatherAgent, LocationAgent]  # add more agents here as you implement them
    planner = PlannerAgent(agent_catalog=plan_catalog)
    plan_obj = planner.plan(user_input)
    plan = plan_obj.get("plan", [])
    logger.info(f"[Orchestrator] Plan: {plan} | Notes: {plan_obj.get('notes')}")

    # 2) Execute plan sequentially
    outputs: Dict[str, str] = {}
    for step in plan:
        agent_name = step.get("agent")
        agent_input = step.get("input") or user_input
        if agent_name not in AGENT_REGISTRY:
            logger.warning(f"[Orchestrator] Unknown agent '{agent_name}', skipping.")
            continue

        agent = _create_agent(AGENT_REGISTRY[agent_name])

        try:
            result = agent.run(agent_input)
        except TypeError as e:
            logger.warning(f"[Orchestrator] run() failed with {e}; retrying with explicit binding.")
            result = BaseAgent.run(agent, agent_input)

        outputs[agent_name] = result

    # 3) Synthesize final answer
    synthesizer = SynthesizerAgent()
    final_answer = synthesizer.synthesize(user_input, outputs)
    return final_answer

if __name__ == "__main__":
    queries = [
        "Tell me information about BEIJING, also tell me the current weather of Beijing",
        "What's the weather in Ha Noi today?",
        "Give me some information about Tokyo",
    ]
    for q in queries:
        logger.info("=" * 60)
        logger.info(f"USER: {q}")
        answer = run_orchestration(q)
        logger.info(f"ASSISTANT: {answer}\n")
        logger.info("\n" + "-" * 60 + "\n")
