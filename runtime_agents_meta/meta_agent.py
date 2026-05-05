"""Meta-agent implementation."""

from dataclasses import dataclass
from typing import Dict, Optional

from runtime_agents.shared.base import AgentResult
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

logger = get_logger(__name__)


@dataclass
class MetaAgent:
    """Single adaptive agent that adapts to each request."""

    llm: LLMClient
    available_tools: Dict[str, Tool]
    prompt_builder: object  # DynamicPromptBuilder
    tool_selector: object  # DynamicToolSelector

    async def run(self, requirement: str, context: str = "") -> AgentResult:
        """Run the meta-agent with dynamic adaptation."""
        logger.info("[META_AGENT] Starting execution")

        # Build dynamic prompt
        system_prompt = await self.prompt_builder.build_prompt(requirement, context)

        # Select relevant tools
        selected_tool_names = await self.tool_selector.select_tools(requirement)
        selected_tools = {
            name: self.available_tools[name]
            for name in selected_tool_names
            if name in self.available_tools
        }

        logger.debug(f"[META_AGENT] Selected {len(selected_tools)} tools")

        # Add tool descriptions to prompt
        tool_catalog = "\n".join([f"- {t.name}: {t.description}" for t in selected_tools.values()])
        system_prompt += f"\n\nAvailable tools:\n{tool_catalog}"

        # Execute
        messages = [
            Message("system", system_prompt),
            Message("user", requirement),
        ]

        output = await self.llm.chat(messages, temperature=0.2)
        logger.info("[META_AGENT] Execution complete")

        return AgentResult(agent_name="Meta-Agent", output=output)
