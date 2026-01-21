"""Parent agent for hierarchical execution."""

from dataclasses import dataclass
from typing import Dict, List

from runtime_agents.shared.base import AgentResult
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

logger = get_logger(__name__)


@dataclass
class ChildAgent:
    """A child agent instance."""

    task: str
    llm: LLMClient
    tools: Dict[str, Tool]

    async def execute(self) -> AgentResult:
        """Execute the child agent."""
        system_prompt = f"You are a specialized agent. Complete this task: {self.task}"
        tool_catalog = "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
        system_prompt += f"\n\nAvailable tools:\n{tool_catalog}"

        messages = [
            Message("system", system_prompt),
            Message("user", self.task),
        ]

        output = await self.llm.chat(messages, temperature=0.2)
        return AgentResult(agent_name=f"Child-{self.task[:20]}", output=output)


class ParentAgent:
    """Manages child agents in hierarchical structure."""

    def __init__(self, llm: LLMClient, available_tools: Dict[str, Tool]):
        self.llm = llm
        self.available_tools = available_tools

    async def spawn_and_execute_children(
        self, sub_tasks: List, context: str = "", parallel: bool = False
    ) -> List[AgentResult]:
        """Spawn and execute child agents for sub-tasks."""
        """Spawn and execute child agents."""
        results = []

        if parallel:
            import anyio
            # Execute in parallel
            async def execute_task(task_desc):
                agent = ChildAgent(
                    task=task_desc.description,
                    llm=self.llm,
                    tools=self.available_tools,  # Children get all tools
                )
                return await agent.execute()

            results = await anyio.gather(*[execute_task(task) for task in sub_tasks])
        else:
            # Sequential execution
            for task in sub_tasks:
                agent = ChildAgent(
                    task=task.description,
                    llm=self.llm,
                    tools=self.available_tools,
                )
                result = await agent.execute()
                results.append(result)

        return results
