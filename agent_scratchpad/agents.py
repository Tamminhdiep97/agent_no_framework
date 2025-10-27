import os
from datetime import datetime
import json
import ast
import uuid
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from loguru import logger

from llm import chat_completion
from config import (
    PROMPT_SYNTHESIZER_AGENT,
    PROMPT_NEWS_AGENT_TEMPLATE,
    PROMPT_MATH_AGENT_TEMPLATE,
    make_planner_prompt,
    make_tool_agent_prompt,
)

import tool as t

TOOL_FUNCS = {
    "get_top_headlines": t.get_top_headlines,
    "search_news_articles": t.search_news_articles,
    "get_news_source_info": t.get_news_source_info,
    "add_numbers": t.add_numbers,
    "subtract_numbers": t.subtract_numbers,
    "multiply_numbers": t.multiply_numbers,
    "divide_numbers": t.divide_numbers,
    "fetch_webpage_summary": t.fetch_webpage_summary,
}

ALL_TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "get_top_headlines",
            "description": "Get today's top global news headline",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news_articles",
            "description": "Search for news articles by topic",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news_source_info",
            "description": "Get background info about a news source",
            "parameters": {"type": "object", "properties": {"source": {"type": "string"}}, "required": ["source"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "Add two numbers together",
            "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subtract_numbers",
            "description": "Subtract second number from first number",
            "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "multiply_numbers",
            "description": "Multiply two numbers",
            "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "divide_numbers",
            "description": "Divide first number by second number",
            "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage_summary",
            "description": "Search DuckDuckGo for information on trusted domains and summarize results",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
            }
        }
    },
]


class PlanStep(BaseModel):
    agent: str = Field(...,
                       description="Name of the agent to call (e.g., 'NewsAgent').")
    input: str = Field(..., description="Input to pass to the agent.")


class PlannerOutput(BaseModel):
    reasoning: str = Field(
        default="", description="Reason on why choosing the plan bellow")
    plan: List[PlanStep] = Field(default_factory=list)
    notes: str = Field(default="", description="Rationale from the planner.")


# -----  scratchpad for agent thoughts -----
class Scratchpad:
    def __init__(self):
        self.thoughts: List[Dict[str, Any]] = []

    def add_thought(self, thought_type: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a thought to the scratchpad"""
        thought = {
            "thought_type": thought_type,
            "content": content,
            "timestamp": uuid.uuid4().hex[:8],
            "metadata": metadata or {}
        }
        self.thoughts.append(thought)

    def get_thoughts(self) -> List[Dict[str, Any]]:
        """Get all thoughts from the scratchpad"""
        return self.thoughts

    def clear(self):
        """Clear all thoughts from the scratchpad"""
        self.thoughts.clear()

    def get_content_by_type(self, thought_type: str) -> List[Dict[str, Any]]:
        """Get thoughts filtered by type"""
        return [thought for thought in self.thoughts if thought["thought_type"] == thought_type]

    def get_scratchpad_text(self) -> str:
        """Get the entire scratchpad as a formatted text"""
        if not self.thoughts:
            return "No thoughts in scratchpad."

        scratchpad_text = "=== AGENT SCRATCHPAD ===\n"
        for thought in self.thoughts:
            scratchpad_text += f"[{thought['thought_type']
                                   }] {thought['content']}\n"
            if thought['metadata']:
                scratchpad_text += f"  Metadata: {thought['metadata']}\n"
        scratchpad_text += "=== END SCRATCHPAD ==="
        return scratchpad_text


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
        self.history.append(
            {"role": "assistant", "content": None, "tool_calls": tool_calls})

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
    DESCRIPTION: str = ""

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
        self.execution_log = []
        # Add scratchpad for internal thoughts
        self.scratchpad = Scratchpad()

    def run(self, user_input: str, max_tool_loops: int = 3) -> str:
        logger.info(f"[{self.name}] Input: {user_input}")
        self.memory.add("user", user_input)

        # Add initial thought to scratchpad
        self.scratchpad.add_thought(
            "initial_analysis", f"Processing user request: {user_input}")

        # First call
        message = chat_completion(
            self.memory.get(), tools=self.my_tool_specs if self.tools_enabled else None)

        loops = 0
        while True:
            loops += 1
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                content = (message.get("content") or "").strip()
                if content:
                    self.memory.add("assistant", content)
                    # Add final thoughts to scratchpad
                    self.scratchpad.add_thought("final_response", content)
                    logger.info(f"[{self.name}] Output: {content}")
                return content

            # record the tool_calls
            self.memory.add_assistant_tool_calls(tool_calls)

            # Add tool selection thought to scratchpad
            tool_names = [tc.get("function", {}).get("name")
                          for tc in tool_calls]
            self.scratchpad.add_thought(
                "tool_selection", f"Selected tools: {tool_names}")

            # execute tools
            for tc in tool_calls:
                call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                fn = tc.get("function", {}).get("name")
                raw_args = tc.get("function", {}).get("arguments") or ""

                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args) if raw_args.strip() else {}
                    except json.JSONDecodeError:
                        logger.warning(f"[{self.name}] Invalid JSON args for {
                                       fn}: {raw_args!r}")
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
                self.execution_log.append(
                    {"tool_call": {"name": fn, "args": args}, "result": str(result)})

                # Add tool execution thought to scratchpad
                self.scratchpad.add_thought("tool_execution", f"Executed {
                                            fn} with args {args}, result: {str(result)}")

                logger.info(f"tool call: name: {fn}, args: {
                            args}, result: {str(result)}")
                # logger.info(f"[{self.name}] Tool result: {result}")

            # ask again
            message = chat_completion(
                self.memory.get(), tools=self.my_tool_specs if self.tools_enabled else None)

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
        agent_catalog: Iterable of agent classes (e.g., [NewsAgent, MathAgent])
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
            response_model=PlannerOutput
        )
        out = (message.get("content") or "").strip()

        # Robust JSON extraction
        try:
            out = ast.literal_eval(out)
            obj = PlannerOutput.model_validate_json(
                json.dumps(out)).model_dump()
            logger.info(f"This is content of planning agent {obj}")
            # Add plan to scratchpad
            self.scratchpad.add_thought(
                "planning_result", f"Generated plan: {obj}")

        except Exception as e:
            logger.warning(
                f"[PlannerAgent] Could not parse JSON, falling back due to: {e}")
            # Fallback heuristic
            plan = []
            lowered = user_input.lower()
            if "news" in lowered or "headlines" in lowered or "article" in lowered:
                plan.append({"agent": "NewsAgent", "input": user_input})
            if any(k in lowered for k in ["calculate", "math", "add", "subtract", "multiply", "divide", "sum"]):
                plan.append({"agent": "MathAgent", "input": user_input})
            obj = {"plan": plan, "notes": "fallback plan"}
            # Add fallback plan to scratchpad
            self.scratchpad.add_thought(
                "planning_result", f"Fallback plan: {obj}")
        return obj


class NewsAgent(BaseAgent):
    DESCRIPTION = "Fetches top headlines, searches news articles, and provides source credibility info."

    def __init__(self):
        my_tool_specs = [
            spec for spec in ALL_TOOL_SPECS
            if spec["function"]["name"] in {
                "get_top_headlines", "search_news_articles", "get_news_source_info", "fetch_webpage_summary"
            }
        ]
        my_tool_instruction = (
            "You can retrieve breaking news, search articles by topic, and verify news source reliability."
        )
        system_prompt = make_tool_agent_prompt(
            agent_name=self.__class__.__name__,
            tool_instruction=my_tool_instruction,
            base_template=PROMPT_NEWS_AGENT_TEMPLATE
        )
        super().__init__(name="NewsAgent", system_prompt=system_prompt, tools_enabled=True)
        self.my_tool_specs = my_tool_specs


class MathAgent(BaseAgent):
    DESCRIPTION = "Performs basic mathematical operations like addition, subtraction, multiplication, and division."

    def __init__(self):
        my_tool_specs = [
            spec for spec in ALL_TOOL_SPECS
            if spec["function"]["name"] in {
                "add_numbers", "subtract_numbers", "multiply_numbers", "divide_numbers"
            }
        ]
        my_tool_instruction = (
            "You can perform basic arithmetic operations including addition, subtraction, "
            "multiplication, and division. Always double-check calculations before providing results."
        )
        system_prompt = make_tool_agent_prompt(
            agent_name=self.__class__.__name__,
            tool_instruction=my_tool_instruction,
            base_template=PROMPT_MATH_AGENT_TEMPLATE,
        )
        super().__init__(name="MathAgent", system_prompt=system_prompt, tools_enabled=True)
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
