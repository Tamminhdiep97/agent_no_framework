# orchestrator.py
import os
from datetime import datetime
import uuid
from typing import Dict
from loguru import logger
import random

from agents import PlannerAgent, NewsAgent, MathAgent, SynthesizerAgent, BaseAgent
import util

AGENT_REGISTRY = {
    "PlannerAgent": PlannerAgent,
    "NewsAgent": NewsAgent,
    "MathAgent": MathAgent,
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
    plan_catalog = [NewsAgent, MathAgent]
    planner = PlannerAgent(agent_catalog=plan_catalog)
    plan_obj = planner.plan(user_input)
    plan = plan_obj.get("plan", [])
    logger.info(f"[Orchestrator] Plan: {
                plan} | Notes: {plan_obj.get('notes')}")

    # 2) Execute plan sequentially
    outputs: Dict[str, str] = {}
    agent_logs = []
    all_scratchpads = {}  # Store all agent scratchpads

    for step in plan:
        agent_name = step.get("agent")
        agent_input = step.get("input") or user_input
        if agent_name not in AGENT_REGISTRY:
            logger.warning(f"[Orchestrator] Unknown agent '{
                           agent_name}', skipping.")
            continue

        agent = _create_agent(AGENT_REGISTRY[agent_name])

        try:
            result = agent.run(agent_input)
        except TypeError as e:
            logger.warning(f"[Orchestrator] run() failed with {
                           e}; retrying with explicit binding.")
            result = BaseAgent.run(agent, agent_input)

        outputs[agent_name] = result
        agent_logs.append(
            {
                "agent": agent_name,
                "input": agent_input,
                "tool_calls": agent.execution_log
            }
        )
        # Store the scratchpad for this agent
        all_scratchpads[agent_name] = agent.scratchpad.get_scratchpad_text()

    # 3) Synthesize final answer
    logger.info(f"Agent log: {agent_logs}")
    synthesizer = SynthesizerAgent()
    final_answer = synthesizer.synthesize(user_input, outputs)

    # Store synthesizer's scratchpad as well
    all_scratchpads["SynthesizerAgent"] = synthesizer.scratchpad.get_scratchpad_text()

    trace = {
        "user_input": user_input,
        "plan": plan,
        "agent_logs": agent_logs,
        "final_answer": final_answer,
        "scratchpads": all_scratchpads
    }
    mermaid_md = util.render_mermaid_trace(trace)
    if mermaid_md.strip().startswith("```mermaid"):
        clean_code = mermaid_md.split("```mermaid", 1)[
            1].split("```", 1)[0].strip()
    else:
        clean_code = mermaid_md.strip()
    logger.info(f"memory: {mermaid_md}")
    # Export
    os.makedirs("trace_logs", exist_ok=True)
    id_file = uuid.uuid4().hex[:8]
    md_path = f"trace_logs/visualize_{id_file}.md"
    util.save_mermaid_to_md(clean_code, md_path)

    # Save trace which includes all scratchpads
    save_trace_with_scratchpads(trace, id_file)

    return final_answer


def save_trace_with_scratchpads(trace: Dict[str, str], id_file):
    """Save the full trace including scratchpads to a file"""

    # Create scratchpad_logs directory if it doesn't exist

    # Sanitize user input for filename
    user_input = trace["user_input"]
    sanitized_input = "".join(
        c if c.isalnum() or c in " _-" else "_" for c in user_input)[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trace_logs/full_trace_{id_file}.json"

    import json
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)

    logger.info(f"Full trace with scratchpads logged to {filename}")


if __name__ == "__main__":
    queries = [
        # "What are today's top headlines?",
        # "Get me the latest news about weather in south Viet Nam",
        # f"What is {random.randint(1, 10000)} plus {random.randint(1, 20000)}?",
        # f"Divide {random.randint(1, 10000)} by {random.randint(1, 20000)}"
        "What is the result of (2^12 + 2^13)*3/2 + 15"
    ]
    for q in queries:
        logger.info("=" * 60)
        logger.info(f"USER: {q}")
        answer = run_orchestration(q)
        # logger.success(f"ASSISTANT: {answer}\n")
        logger.info("\n" + "-" * 60 + "\n")
