# llm.py
import requests
from typing import List, Dict, Any, Optional, Type

from pydantic import BaseModel
from loguru import logger

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, REQUEST_TIMEOUT, DEFAULT_TEMPERATURE

def chat_completion(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = "auto",
    temperature: float = DEFAULT_TEMPERATURE,
    response_model: Optional[Type["BaseModel"]] = None,
) -> Dict[str, Any]:
    """
    Call an OpenAI-compatible /chat/completions endpoint using requests.
    Returns the assistant message dict: {"role": "...", "content": "...", "tool_calls": [...]}
    """
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if response_model is not None:
        schema = response_model.model_json_schema()
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__.lower(),
                "strict": True,
                "schema": schema,
            },
        }
    if tools is not None:
        payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

    logger.debug(f"POST {OPENAI_BASE_URL}/chat/completions")
    resp = requests.post(f"{OPENAI_BASE_URL}/chat/completions", json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    message = data["choices"][0]["message"]
    logger.debug(message)
    return message
