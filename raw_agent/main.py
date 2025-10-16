import time
import json
import uuid

import requests
from loguru import logger

from tool import *

# === CONFIG ===
OPENAI_API_KEY = "your_api_key_here"
OPENAI_BASE_URL = "http://localhost:7676/v1"
OPENAI_MODEL = "Qwen3-14B-AWQ"

TOOL_FUNCS = {
    "get_weather": get_weather,
    "search_location_info": search_location_info,
}

tools = [
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
            }
        }
    }
]

# === MEMORY ===
class Memory:
    def __init__(self):
        self.history = []

    def add(self, role, content):
        self.history.append({"role": role, "content": content})

    def add_assistant_tool_calls(self, tool_calls):
        # Standard OpenAI-compatible shape: one assistant msg with tool_calls
        self.history.append({"role": "assistant", "content": None, "tool_calls": tool_calls})

    def add_tool_result(self, tool_call_id, name, result):
        # Standard OpenAI-compatible shape for tool result
        self.history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": str(result),
        })

    def get(self):
        return self.history

# === OPENAI-COMPATIBLE CALL ===
def chat_completion(messages):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",     # allow model to choose tools
    }
    resp = requests.post(f"{OPENAI_BASE_URL}/chat/completions", headers=headers, json=data, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    logger.debug(payload)
    return payload["choices"][0]["message"]

# === AGENT STEP ===
def agent_step(memory, user_input, max_tool_loops=3):
    # 1) Observe: add user message
    memory.add("user", user_input)

    # 2) First plan: ask the model
    message = chat_completion(memory.get())

    # 3) Act/loop on tool calls until the model replies normally or we hit a limit
    loops = 0
    while True:
        loops += 1
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            # No tool calls: final assistant content
            if message.get("content"):
                memory.add("assistant", message["content"])
                logger.info(f"Assistant: {message['content']}")
            break

        # Add the assistant message with tool_calls to the history
        memory.add_assistant_tool_calls(tool_calls)

        # Execute each tool call and append the tool results
        for idx, tool_call in enumerate(tool_calls):
            # Fallback: generate an id if the server didn't attach one
            call_id = tool_call.get("id") or f"call_{uuid.uuid4().hex[:8]}"

            func_name = tool_call.get("function", {}).get("name")
            raw_args = tool_call.get("function", {}).get("arguments", "")

            # vLLM/OpenAI tool calls commonly return arguments as a JSON string
            # Parse robustly (string or dict)
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args) if raw_args.strip() else {}
                except json.JSONDecodeError:
                    logger.warning(f"Arguments were not valid JSON: {raw_args!r}. Using empty dict.")
                    args = {}
            elif isinstance(raw_args, dict):
                args = raw_args
            else:
                args = {}

            logger.info(f"Tool call #{idx+1}: {func_name}({args})")

            if func_name not in TOOL_FUNCS:
                result = f"Error: unknown tool '{func_name}'."
            else:
                func = TOOL_FUNCS.get(func_name)
                try:
                    result = func(**args)
                except TypeError as e:
                    result = f"Error when invoking '{func_name}': {e}"

            memory.add_tool_result(call_id, func_name, result)
            logger.info(f"Tool result: {result}")

        # 4) Ask the model again with tool outputs available
        message = chat_completion(memory.get())

        if loops >= max_tool_loops:
            logger.warning("Max tool loops reached; stopping.")
            # If still tool-calling, exit gracefully
            if message.get("content"):
                memory.add("assistant", message["content"])
            break

# === MAIN LOOP ===
def run_agent():
    memory = Memory()
    memory.add("system", "You are a helpful agent with ability to use tools to answer questions.")
    user_inputs = [
        # "What's the weather in Ho Chi Minh City?",
        # "What's the weather in Ha Noi?",
        # "What's the weather in Tokyo?",
        # "What's the weather in London?",
        "Tell me information about BEIJING, also tell me the current weather of Beijing"
    ]

    for step, user_input in enumerate(user_inputs, start=1):
        time.sleep(0.5)
        logger.info(f"---------- Step {step} ----------")
        logger.info(f"Input: {user_input}")
        agent_step(memory, user_input)

# === RUN ===
if __name__ == "__main__":
    run_agent()
