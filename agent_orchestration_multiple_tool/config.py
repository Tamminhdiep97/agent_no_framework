from dotenv import dotenv_values

env = dotenv_values(".env")

OPENAI_API_KEY = env["OPENAI_API_KEY"]
OPENAI_BASE_URL = env["OPENAI_BASE_URL"]
OPENAI_MODEL = env["OPENAI_MODEL"]

NEWS_API_KEY = env["NEWS_API_KEY"] if env["NEWS_API_KEY"] != "None" else None
EDAMAM_APP_ID = env["EDAMAM_APP_ID"] if env["EDAMAM_APP_ID"] != "None" else None
EDAMAM_APP_KEY = env["EDAMAM_APP_KEY"] if env["EDAMAM_APP_KEY"] != "None" else None


REQUEST_TIMEOUT = 120
DEFAULT_TEMPERATURE = 0.2

# -----------------------------

PROMPT_PLANNER_TEMPLATE = """
You are PlannerAgent.

Your task:
- Decide which specialist agents (from the catalog below) should handle the user request.
- Extract clean inputs for each agent
- Return STRICT JSON only (no extra text) with this schema:
{{
  "reasoning": "Your thought process: interpret the request, map needs to agent capabilities, justify inclusions/exclusions."
  "plan": [
    {{"agent": "<AgentName>", "input": "<string>"}}
    // You may include multiple steps; order matters.
  ],
  "notes": "<short rationale>"
}}

Catalog of available agents (names + capabilities):
{AGENT_LIST}

Guidelines:
- Choose the minimal set of agents that fully addresses the request.
- If the user asks for multiple things, include multiple steps in a sensible order.
- If no agent applies, return {{"plan": [], "notes": "no applicable agent"}}.
- Do NOT include agents not listed in the catalog. Do NOT include SynthesizerAgent in the plan.
- Output JSON ONLY — no markdown, no prose.
"""

# Base template for agents that use tools - includes a placeholder for tool instruction
PROMPT_AGENT_WITH_TOOLS_TEMPLATE = """
You are {AGENT_NAME}.
{TOOL_INSTRUCTION}
"""

PROMPT_SYNTHESIZER_AGENT = """
You are SynthesizerAgent.
Given the user's request and the intermediate agent outputs, compose a clear, concise final answer.
Preserve key facts and avoid redundancy.
"""

PROMPT_NEWS_AGENT_TEMPLATE = PROMPT_AGENT_WITH_TOOLS_TEMPLATE + """
Use your tools to fetch headlines, search articles, or verify source credibility.
Respond concisely and cite sources when possible.
"""

PROMPT_HEALTH_AGENT_TEMPLATE = PROMPT_AGENT_WITH_TOOLS_TEMPLATE + """
Use your tools to provide nutrition facts, general symptom info, or clinic locations.
Always remind users to consult a professional for medical advice.
"""

# -------------------------------------------
# Helper: build the PlannerAgent prompt at run-time
# -------------------------------------------

def make_planner_prompt(agent_classes):
    """
    Build a generalized planner prompt from agent classes.
    Expects each class to expose a `DESCRIPTION` attribute.
    """
    lines = []
    for cls in agent_classes:
        name = getattr(cls, "__name__", "UnknownAgent")
        desc = getattr(cls, "DESCRIPTION", "").strip()
        if not desc:
            desc = "(no description provided)"
        lines.append(f"- {name}: {desc}")
    agent_list = "\n".join(lines) if lines else "- (none)"
    return PROMPT_PLANNER_TEMPLATE.replace("{AGENT_LIST}", agent_list)

# Helper: build the system prompt for an agent with tools
def make_tool_agent_prompt(agent_name: str, tool_instruction: str, base_template: str = PROMPT_AGENT_WITH_TOOLS_TEMPLATE):
    """
    Builds a system prompt for an agent based on its name and a specific instruction about its tools.
    """
    # Format the base template with the agent's name and its specific tool instruction
    return base_template.format(
        AGENT_NAME=agent_name,
        TOOL_INSTRUCTION=tool_instruction
    )
