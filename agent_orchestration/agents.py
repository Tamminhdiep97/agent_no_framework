import json
import uuid
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from loguru import logger

from llm import chat_completion
from config import (
    PROMPT_WEATHER_AGENT_TEMPLATE,
    PROMPT_LOCATION_AGENT_TEMPLATE,
    PROMPT_SYNTHESIZER_AGENT,
    make_planner_prompt,
    make_tool_agent_prompt,
)

from tool import get_weather, search_location_info

TOOL_FUNCS = {
    "get_weather": get_weather,
    "search_location_info": search_location_info,
}

ALL_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_location_info",
            "description": "Get information about a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                },
                "required": ["location"],
            },
        },
    },
]


class PlanStep(BaseModel):
    agent: str = Field(..., description="Name of the agent to call (e.g., 'WeatherAgent').")
    input: str = Field(..., description="Input to pass to the agent.")

class PlannerOutput(BaseModel):
    plan: List[PlanStep] = Field(default_factory=list)
    notes: str = Field(default="", description="Rationale from the planner.")

# -----  memory per agent -----
class Memory:
    def __init__(self, system_prompt: str):
        self.history: List[Dict[str, Any]] = []
        if system_prompt:
            self.add("system", system_prompt)

    def add(self, role: str, content: Optional[str], **kwargs):
        msg = {"role": role, "content": content}
        msg.update(kwargs)
        self.history.append(msg)

    def add_assistant_tool_calls(self, tool_calls: List[Dict[str, Any]]):
        self.history.append({"role": "assistant", "content": None, "tool_calls": tool_calls})

    def add_tool_result(self, tool_call_id: str, name: str, result: Any):
        self.history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": str(result),
        })

    def get(self) -> List[Dict[str, Any]]:
        return self.history


# ----- BaseAgent -----
class BaseAgent:
    DESCRIPTION: str = ""  # Each agent should override this

    def __init__(self, name: str, system_prompt: str, tools_enabled: bool = False, memory=None):
        self.name = name
        self.system_prompt = system_prompt
        self.tools_enabled = tools_enabled
        self.my_tool_specs = []
        # Allow injected shared memory, otherwise private memory
        if memory is not None:
            self.memory = memory
            # Ensure system prompt is present in this channel
            self.memory.add("system", system_prompt)
        else:
            self.memory = Memory(system_prompt)

    def run(self, user_input: str, max_tool_loops: int = 3) -> str:
        logger.info(f"[{self.name}] Input: {user_input}")
        self.memory.add("user", user_input)

        # First call
        message = chat_completion(self.memory.get(), tools=self.my_tool_specs if self.tools_enabled else None)

        loops = 0
        while True:
            loops += 1
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                content = (message.get("content") or "").strip()
                if content:
                    self.memory.add("assistant", content)
                    logger.info(f"[{self.name}] Output: {content}")
                return content

            # record the tool_calls
            self.memory.add_assistant_tool_calls(tool_calls)

            # execute tools
            for tc in tool_calls:
                call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                fn = tc.get("function", {}).get("name")
                raw_args = tc.get("function", {}).get("arguments") or ""

                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args) if raw_args.strip() else {}
                    except json.JSONDecodeError:
                        logger.warning(f"[{self.name}] Invalid JSON args for {fn}: {raw_args!r}")
                        args = {}
                elif isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = {}

                logger.info(f"[{self.name}] Tool call: {fn}({args})")
                if fn not in TOOL_FUNCS:
                    result = f"Error: unknown tool '{fn}'."
                else:
                    try:
                        result = TOOL_FUNCS[fn](**args)
                    except TypeError as e:
                        result = f"Error invoking '{fn}': {e}"
                    except Exception as e:
                        result = f"Tool '{fn}' failed: {e}"

                self.memory.add_tool_result(call_id, fn, result)
                logger.info(f"[{self.name}] Tool result: {result}")

            # ask again
            message = chat_completion(self.memory.get(), tools=self.my_tool_specs if self.tools_enabled else None)

            if loops >= max_tool_loops:
                logger.warning(f"[{self.name}] Max tool loops reached.")
                content = (message.get("content") or "").strip()
                if content:
                    self.memory.add("assistant", content)
                return content


# ----- Specialized Agents -----
class PlannerAgent(BaseAgent):
    DESCRIPTION = "Plans which specialist agents to call and extracts clean inputs for each step."

    def __init__(self, agent_catalog=None, system_prompt: Optional[str] = None):
        """
        agent_catalog: Iterable of agent classes (e.g., [WeatherAgent, LocationAgent])
        system_prompt: if provided, overrides the auto-built prompt
        """
        # Build a generalized prompt from catalog if none provided
        if system_prompt is None:
            agent_catalog = agent_catalog or []
            system_prompt = make_planner_prompt(agent_catalog)
        super().__init__(name="PlannerAgent", system_prompt=system_prompt, tools_enabled=False)

    def plan(self, user_input: str) -> Dict[str, Any]:
        # Force JSON if supported by the server
        self.memory.add("user", user_input)
        message = chat_completion(
            self.memory.get(),
            tools=None,
            response_format={"type": "json_object"}  # helps produce clean JSON on compatible servers
        )
        out = (message.get("content") or "").strip()

        # Robust JSON extraction
        try:
            start = out.find("{")
            end = out.rfind("}")
            obj = json.loads(out[start:end + 1])
        except Exception as e:
            logger.warning(f"[PlannerAgent] Could not parse JSON, falling back due to: {e}")
            # Fallback heuristic
            plan = []
            lowered = user_input.lower()
            if "weather" in lowered:
                plan.append({"agent": "WeatherAgent", "input": user_input})
            if any(k in lowered for k in ["info", "information", "about", "tell me about", "where is"]):
                plan.append({"agent": "LocationAgent", "input": user_input})
            obj = {"plan": plan, "notes": "fallback plan"}
        return obj


class WeatherAgent(BaseAgent):
    DESCRIPTION = "Fetches current weather information for a specified location."

    def __init__(self):
        # Define the specific tools this agent has access to
        my_tool_specs = [ALL_TOOL_SPECS[0]]
        # Define the specific instruction for these tools
        my_tool_instruction = "You have access to a tool that retrieves the current weather for a given location."

        # Dynamically generate the system prompt using the helper function
        system_prompt = make_tool_agent_prompt(
            agent_name=self.__class__.__name__,
            tool_instruction=my_tool_instruction,
            base_template=PROMPT_WEATHER_AGENT_TEMPLATE
        )
        super().__init__(
            name="WeatherAgent",
            system_prompt=system_prompt,
            tools_enabled=True,
        )
        self.my_tool_specs = my_tool_specs


class LocationAgent(BaseAgent):
    DESCRIPTION = "Provides summarized information about a specified location, including details like coordinates and relevant links if available."

    def __init__(self):
        # Define the specific tools this agent has access to
        my_tool_specs = [ALL_TOOL_SPECS[1]]
        # Define the specific instruction for these tools
        my_tool_instruction = "You have access to a tool that retrieves information about a given location."

        # Dynamically generate the system prompt using the helper function
        system_prompt = make_tool_agent_prompt(
            agent_name=self.__class__.__name__,
            tool_instruction=my_tool_instruction,
            base_template=PROMPT_LOCATION_AGENT_TEMPLATE
        )
        super().__init__(
            name="LocationAgent",
            system_prompt=system_prompt,
            tools_enabled=True,
        )
        self.my_tool_specs = my_tool_specs


class SynthesizerAgent(BaseAgent):
    DESCRIPTION = "Combines intermediate agent outputs into a concise final answer."

    def __init__(self):
        super().__init__(
            name="SynthesizerAgent",
            system_prompt=PROMPT_SYNTHESIZER_AGENT,
            tools_enabled=False,
        )

    def synthesize(self, user_input: str, intermediate: Dict[str, str]) -> str:
        # Build a prompt for the LLM to combine results
        parts = [f"User request: {user_input}", "Agent outputs:"]
        for k, v in intermediate.items():
            parts.append(f"- {k}: {v}")
        parts.append("Compose a concise final answer for the user.")
        prompt = "\n".join(parts)
        return self.run(prompt)
