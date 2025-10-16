import requests
from typing import List
from pydantic import BaseModel
import json

from loguru import logger

# === CONFIG ===
OPENAI_API_KEY = "your_api_key_here"
OPENAI_BASE_URL = "http://localhost:7676/v1"
OPENAI_MODEL = "Qwen3-14B-AWQ"

class Step(BaseModel):
    explanation: str
    output: str


class MathResponse(BaseModel):
    steps: List[Step]
    final_answer: str


def model_to_json_schema(model_cls) -> dict:
    """Return a JSON Schema for the given Pydantic model, v1/v2 compatible."""
    try:
        # Pydantic v2
        return model_cls.model_json_schema()
    except AttributeError:
        # Pydantic v1
        return model_cls.schema()


def validate_against_model(model_cls, data):
    """Validate data with the model, v1/v2 compatible."""
    try:
        # Pydantic v2
        return model_cls.model_validate(data)
    except AttributeError:
        # Pydantic v1
        return model_cls.parse_obj(data)

# Define the request payload
payload = {
    "model": OPENAI_MODEL,
    "messages": [
        {"role": "system", "content": "You are a helpful expert math tutor."},
        {"role": "user", "content": "Solve 8x + 31 = 2."}
    ],

    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": MathResponse.__name__.lower(),
            "schema": model_to_json_schema(MathResponse),
            "strict": True,
            }
    },
}
headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

# Send the request
response = requests.post(
    f"{OPENAI_BASE_URL}/chat/completions",
    headers=headers,
    json=payload
)

# Check for errors
response.raise_for_status()
data = response.json()
content = data["choices"][0]["message"].get("content")
logger.info(f"content: {content}")
# Extract and parse the structured response
parsed = validate_against_model(MathResponse, json.loads(content))
# Print the steps and final answer


for i, step in enumerate(parsed.steps):
    logger.info(f"Step # {i}: {step}")
logger.info(f"Answer: {parsed.final_answer}")

