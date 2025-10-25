# agent_no_framework

This repository demonstrates a lightweight agent orchestration system in Python, designed for multi-agent coordination and tool usage without relying on heavy frameworks. It provides a set of agents that interact with OpenAI-compatible language models and external APIs to answer queries about weather and locations, and supports structured outputs for tutoring-like applications.

## Features

- **Agent Orchestration**: Modular agent classes (PlannerAgent, WeatherAgent, LocationAgent, SynthesizerAgent) coordinated by an Orchestrator.
- **Tool Integration**: Agents use built-in tools to fetch weather data and look up location information via Wikipedia.
- **OpenAI-Compatible API**: Interacts with OpenAI-compatible endpoints for chat completions, supporting tool calls and structured responses.
- **Memory Management**: Each agent maintains its own message history for contextual conversations.
- **Structured Output Example**: Includes a math tutor that validates and parses structured responses using Pydantic models.

## Project Structure

- `raw_agent/`  
  - `main.py`: Example standalone agent with tool usage and OpenAI-compatible API calls.
  - `tool.py`: Implements weather lookup and Wikipedia-based location info retrieval.

- `agent_orchestration/`  
  - `config.py`: Configuration and prompt templates for different agent roles.
  - `agents.py`: Agent class implementations and memory handling.
  - `orchestrator.py`: Logic for planning, executing, and synthesizing multi-agent workflows.
  - `llm.py`: Utility for calling the OpenAI-compatible API.

- `agent_orchestration_multiple_tool/`  
  - `agents.py`: Advanced agent class implementations with multiple specialized agents (NewsAgent, HealthAgent, etc.) and shared memory capabilities.
  - `config.py`: Configuration settings and prompt templates for multi-tool agents.
  - `llm.py`: Utility for calling the OpenAI-compatible API with structured response support.
  - `main.py`: Orchestrator logic for coordinating multi-tool agent workflows.
  - `tool.py`: Collection of specialized tools for news, health, and web scraping functionalities.
  - `util.py`: Utility functions for visualization and trace logging.
  - `requirements.txt`: Dependencies for the multi-tool agent system.
  - `env.example`: Example environment configuration file.

- `structed_output/`  
  - `main.py`: Example of structured output for math tutoring, using Pydantic for schema validation.

## How It Works

1. **Planning**: The planner agent decides which specialist agents handle each part of the user's request.
2. **Execution**: The orchestrator runs the selected agents, calling tools as needed.
3. **Synthesis**: Results from agents are combined into a final, user-facing answer.

## Example Use Cases

- "What's the weather in Ha Noi today?"  
- "Tell me information about BEIJING, also tell me the current weather of Beijing."
- "Give me some information about Tokyo."
- "Solve 8x + 31 = 2." (math tutoring with structured response)

## Requirements

- Python 3.12+
- `requests`
- `loguru`
- `pydantic`

## Setup

1. Install dependencies:
   ```bash
   pip install requests loguru pydantic
   ```
   or
   ```bash
   pip install -r requirements.txt
   ```
3. Configure your OpenAI-compatible API credentials in `config.py`.

## License

This project is licensed under The Unlicense.

## Future Work

- **Agent Scratchpad + Long Term Memory**: Implement advanced memory systems that allow agents to maintain working scratchpads for complex reasoning tasks and long-term memory stores for retaining important information across sessions.

- **Conversation Capability**: Enhance the agents to support multi-turn conversations, tracking context and allowing more natural, continuous interactions.

- **Chat-History Database**: Integrate a database (e.g., SQLite, PostgreSQL, or Redis) to persist chat histories, enabling session continuity and retrieval.

- **Manual MCP Service**: Plan to develop and integrate manual MCP code that can serve tool functionalities in a dedicated, separate service. This allows for better modularization and scalability of the tool-serving architecture.

- **Multi-User Support**: Implement robust database handling to manage chat histories for multiple users, ensuring separation, privacy, and efficient access.

- **Load Balancing**: Develop mechanisms to balance requests and database writes across multiple users, improving scalability and reliability for concurrent interactions.
- Additional improvements and features will be documented here as the project evolves.

---

*For more details, see the [GitHub repository](https://github.com/Tamminhdiep97/agent_no_framework).*
