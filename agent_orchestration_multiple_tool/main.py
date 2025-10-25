# orchestrator.py
import uuid
from typing import Dict
from loguru import logger
from agents import PlannerAgent, NewsAgent, HealthAgent, SynthesizerAgent, BaseAgent
import util

AGENT_REGISTRY = {
    "PlannerAgent": PlannerAgent,
    "NewsAgent": NewsAgent,
    "HealthAgent": HealthAgent,
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
    plan_catalog = [NewsAgent, HealthAgent]
    planner = PlannerAgent(agent_catalog=plan_catalog)
    plan_obj = planner.plan(user_input)
    plan = plan_obj.get("plan", [])
    logger.info(f"[Orchestrator] Plan: {plan} | Notes: {plan_obj.get('notes')}")

    # 2) Execute plan sequentially
    outputs: Dict[str, str] = {}
    agent_logs = []

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
        agent_logs.append(
            {
                "agent": agent_name,
                "input": agent_input,
                "tool_calls": agent.execution_log
            }
        )

    # 3) Synthesize final answer
    logger.info(f"Agent log: {agent_logs}")
    synthesizer = SynthesizerAgent()
    final_answer = synthesizer.synthesize(user_input, outputs)
    trace = {
        "user_input": user_input,
        "plan": plan,
        "agent_logs": agent_logs,
        "final_answer": final_answer
    }
    mermaid_md = util.render_mermaid_trace(trace)
    if mermaid_md.strip().startswith("```mermaid"):
        clean_code = mermaid_md.split("```mermaid", 1)[1].split("```", 1)[0].strip()
    else:
        clean_code = mermaid_md.strip()
    logger.info(f"memory: {mermaid_md}")
    # Export
    md_path = f"trace_{uuid.uuid4().hex[:8]}.md"
    util.save_mermaid_to_md(clean_code, md_path)

    return final_answer


if __name__ == "__main__":
    queries = [
        # "What are today's top headlines? Also, is BBC a trustworthy source?",
        # "I have a headache and want to eat a hamburger. Is that good? Find clinics near London."
        "I have a headache, what could be the reason, also, find clinics near London"
    ]
    for q in queries:
        logger.info("=" * 60)
        logger.info(f"USER: {q}")
        answer = run_orchestration(q)
        # logger.success(f"ASSISTANT: {answer}\n")
        logger.info("\n" + "-" * 60 + "\n")
