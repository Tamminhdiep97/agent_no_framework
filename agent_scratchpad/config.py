from dotenv import dotenv_values

env = dotenv_values(".env")

OPENAI_API_KEY = env["OPENAI_API_KEY"]
OPENAI_BASE_URL = env["OPENAI_BASE_URL"]
OPENAI_MODEL = env["OPENAI_MODEL"]

NEWS_API_KEY = env["NEWS_API_KEY"] if env["NEWS_API_KEY"] != "None" else None
EDAMAM_APP_ID = env["EDAMAM_APP_ID"] if env["EDAMAM_APP_ID"] != "None" else None
EDAMAM_APP_KEY = env["EDAMAM_APP_KEY"] if env["EDAMAM_APP_KEY"] != "None" else None

ALLOWED_DOMAINS = [
    "medlineplus.gov",
    "nih.gov",
    "who.int",
    "cdc.gov",
    "mayoclinic.org",
    "webmd.com",
    "www.google.com",
    "wsearch.nlm.nih.gov",
]

REQUEST_TIMEOUT = 120
DEFAULT_TEMPERATURE = 0.2

# -----------------------------

PROMPT_PLANNER_TEMPLATE = """
You are PlannerAgent.

Your task:
- Think through the user request step by step in your scratchpad
- Decide which specialist agents (from the catalog below) should handle the user request
- Extract clean inputs for each agent
- Document your reasoning in your scratchpad as you work
- Return STRICT JSON only (no extra text) with this schema:
{{
  "reasoning": "Your thought process: interpret the request, map needs to agent capabilities, justify inclusions/exclusions.",
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
Before providing your final answer, think through the user's request step by step.
Document your analysis in your scratchpad thoughts, including your reasoning for using tools and interpreting results.
If you need additional information from trusted sources, you can use the fetch_webpage_summary tool to search DuckDuckGo.
{TOOL_INSTRUCTION}
"""

PROMPT_SYNTHESIZER_AGENT = """
You are SynthesizerAgent.
Given the user's request and the intermediate agent outputs, think through how to best combine the information step by step.
Document your synthesis process in your scratchpad thoughts as you work.
Compose a clear, concise final answer that preserves key facts and avoids redundancy.
"""

PROMPT_NEWS_AGENT_TEMPLATE = PROMPT_AGENT_WITH_TOOLS_TEMPLATE + """
Use your tools to fetch headlines, search articles, or verify source credibility.
When you need additional information from trusted sources, consider using the fetch_webpage_summary tool to search DuckDuckGo.
Think through what news information is most relevant to the user's request.
Document your analysis of news content in your scratchpad thoughts.
Respond concisely and cite sources when possible.
"""

PROMPT_HEALTH_AGENT_TEMPLATE = PROMPT_AGENT_WITH_TOOLS_TEMPLATE + """
Use your tools to provide nutrition facts, general symptom info, or clinic locations.
Think through health-related queries carefully, considering safety and accuracy.
Document your reasoning and safety considerations in your scratchpad thoughts.
Always remind users to consult a professional for medical advice.
"""

PROMPT_MATH_AGENT_TEMPLATE = PROMPT_AGENT_WITH_TOOLS_TEMPLATE + """
Use your tools to perform mathematical calculations.
If the user's request requires additional context or information beyond basic math, consider using the fetch_webpage_summary tool to search for relevant information.
Think through the math problem step by step before providing the answer.
Document your calculation process in your scratchpad thoughts.
Make sure to handle division by zero errors appropriately.
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

