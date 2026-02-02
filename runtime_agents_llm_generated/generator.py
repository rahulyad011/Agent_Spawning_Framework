"""Agent specification generator using LLM."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from runtime_agents.shared.base import AgentResult
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

logger = get_logger(__name__)


@dataclass
class AgentSpec:
    """Generated agent specification."""

    role: str
    system_prompt: str
    tool_names: List[str]
    name: str = ""


class DynamicAgentGenerator:
    """Generates agent specifications dynamically using LLM."""

    def __init__(self, llm: LLMClient, available_tools: Dict[str, Tool], temperature: float = 0.7):
        self.llm = llm
        self.available_tools = available_tools
        self.temperature = temperature

    async def generate_agent_spec(
        self, requirement: str, max_agents: int = 3
    ) -> List[AgentSpec]:
        """Generate agent specifications for a requirement."""
        logger.info(f"[GENERATOR] Generating agent specs for: {requirement[:100]}...")

        tool_descriptions = "\n".join(
            [f"- {name}: {tool.description}" for name, tool in self.available_tools.items()]
        )

        prompt = f"""Based on this user requirement: "{requirement}"

Create {max_agents} agent specifications that would best handle this task.
If the user asks to analyze, read, or examine a file, CSV, or dataset, at least one agent MUST include the "file_read" tool so the file content can be read.

For each agent, specify:
1. role: What this agent's role should be
2. name: A descriptive name for this agent
3. system_prompt: Detailed instructions for how this agent should behave
4. tool_names: Which tools from the available tools this agent should use

Available tools:
{tool_descriptions}

Return a JSON array with {max_agents} agent objects:
[
  {{
    "role": "data analyst",
    "name": "Data Analyst",
    "system_prompt": "You are a data analyst...",
    "tool_names": ["file_read", "db_query"]
  }},
  ...
]
"""

        try:
            response = await self.llm.chat(
                [Message("user", prompt)], temperature=self.temperature
            )
            logger.debug(f"[GENERATOR] LLM response: {response[:200]}...")

            # Try to extract JSON from response
            json_start = response.find("[")
            json_end = response.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                specs_data = json.loads(json_str)
            else:
                # Fallback: try to parse entire response
                specs_data = json.loads(response)

            specs = []
            for spec_data in specs_data:
                # Validate tool names exist
                valid_tools = [
                    name
                    for name in spec_data.get("tool_names", [])
                    if name in self.available_tools
                ]
                spec = AgentSpec(
                    role=spec_data.get("role", "agent"),
                    name=spec_data.get("name", spec_data.get("role", "agent")),
                    system_prompt=spec_data.get("system_prompt", ""),
                    tool_names=valid_tools,
                )
                specs.append(spec)
                logger.debug(f"[GENERATOR] Generated spec: {spec.name} with tools: {valid_tools}")

            return specs

        except Exception as e:
            logger.warning(f"[GENERATOR] Error generating specs: {e}, using fallback")
            # Fallback: create a simple agent
            return [
                AgentSpec(
                    role="general assistant",
                    name="Assistant",
                    system_prompt=f"You help the user with: {requirement}",
                    tool_names=list(self.available_tools.keys())[:3],
                )
            ]
