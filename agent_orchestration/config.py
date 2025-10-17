# config.py
OPENAI_API_KEY = "your_api_key_here"
OPENAI_BASE_URL = "http://localhost:7676/v1"
OPENAI_MODEL = "Qwen3-4B-AWQ"

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

# Specific templates using the placeholder
PROMPT_WEATHER_AGENT_TEMPLATE = PROMPT_AGENT_WITH_TOOLS_TEMPLATE + """
Specifically, use the appropriate tool to find the weather for a location.
Respond with a short human-readable summary, e.g.: "Beijing: ☁️ +12°C".
"""

PROMPT_LOCATION_AGENT_TEMPLATE = PROMPT_AGENT_WITH_TOOLS_TEMPLATE + """
Specifically, use the appropriate tool to gather information about a location.
Return a concise summary (3–6 sentences) and include coordinates and URL if available.
"""

PROMPT_SYNTHESIZER_AGENT = """
You are SynthesizerAgent.
Given the user's request and the intermediate agent outputs, compose a clear, concise final answer.
Preserve key facts and avoid redundancy.
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
