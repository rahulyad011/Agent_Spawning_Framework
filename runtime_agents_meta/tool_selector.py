"""Dynamic tool selector for meta-agent."""

from typing import Dict, List

from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

logger = get_logger(__name__)


class DynamicToolSelector:
    """Selects tools dynamically based on requirements."""

    def __init__(self, llm: LLMClient, available_tools: Dict[str, Tool]):
        self.llm = llm
        self.available_tools = available_tools

    async def select_tools(self, requirement: str) -> List[str]:
        """Select relevant tools for the requirement."""
        logger.debug("[TOOL_SELECTOR] Selecting tools dynamically")

        tool_descriptions = "\n".join(
            [f"- {name}: {tool.description}" for name, tool in self.available_tools.items()]
        )

        prompt = f"""User requirement: {requirement}

Available tools:
{tool_descriptions}

Which tools are needed to complete this task? Return a comma-separated list of tool names.
Only include tools that are actually needed."""

        try:
            response = await self.llm.chat([Message("user", prompt)], temperature=0.3)
            selected = [name.strip() for name in response.split(",")]
            # Validate tool names exist
            valid_tools = [name for name in selected if name in self.available_tools]
            logger.debug(f"[TOOL_SELECTOR] Selected tools: {valid_tools}")
            return valid_tools
        except Exception as e:
            logger.warning(f"[TOOL_SELECTOR] Error selecting tools: {e}, using all tools")
            return list(self.available_tools.keys())
