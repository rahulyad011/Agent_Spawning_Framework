"""Orchestrator for compositional agents."""

import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

from runtime_agents.shared.base import BaseOrchestrator, ExecutionMetrics
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

from .composer import CompositionEngine, ComposedAgent
from .components import ComponentLibrary

logger = get_logger(__name__)


@dataclass
class ComposedAgentInstance:
    """Instance of a composed agent."""

    composed: ComposedAgent
    llm: LLMClient
    tools: Dict[str, Tool]

    async def run(self, user_input: str, *, context: str = None):
        """Run the composed agent."""
        from runtime_agents.shared.base import AgentResult

        sys_prompt = self.composed.system_prompt
        if context:
            sys_prompt += f"\n\nContext:\n{context}"

        tool_catalog = "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
        sys_prompt += f"\n\nAvailable tools:\n{tool_catalog}"

        messages = [
            Message("system", sys_prompt),
            Message("user", user_input),
        ]

        output = await self.llm.chat(messages, temperature=0.2)
        return AgentResult(agent_name=self.composed.name, output=output)


@dataclass
class CompositionalOrchestrator(BaseOrchestrator):
    """Orchestrator that composes agents from reusable components."""

    available_tools: Dict[str, Tool]
    component_library: ComponentLibrary = None
    _last_metrics: ExecutionMetrics = None

    def __init__(
        self,
        llm: LLMClient,
        available_tools: Dict[str, Tool],
        session_context: str = "",
        component_library: ComponentLibrary = None,
    ):
        super().__init__(llm, session_context)
        self.available_tools = available_tools
        self.component_library = component_library or ComponentLibrary()
        self.composer = CompositionEngine(self.component_library)

    async def run(self, requirement: str) -> Tuple[List, str]:
        """Run with composed agents."""
        start_time = time.time()
        logger.info(f"[COMP_ORCH] Starting execution for: {requirement[:100]}...")

        # Compose agent
        composed = self.composer.compose_agent(requirement)
        logger.info(f"[COMP_ORCH] Composed agent: {composed.name}")

        # Create instance
        scoped_tools = {
            name: self.available_tools[name]
            for name in composed.tool_names
            if name in self.available_tools
        }
        agent = ComposedAgentInstance(composed=composed, llm=self.llm, tools=scoped_tools)

        # Execute
        result = await agent.run(requirement, context=self.session_context)
        results = [result]

        # Aggregate (single agent, so just return its output)
        final = result.output

        execution_time = time.time() - start_time
        self._last_metrics = ExecutionMetrics(
            agent_type="compositional",
            execution_time=execution_time,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=1,
            tool_calls_count=len(result.tool_calls),
        )

        logger.info(f"[COMP_ORCH] Execution complete in {execution_time:.2f}s")
        return results, final

    def get_metrics(self) -> ExecutionMetrics:
        """Get performance metrics."""
        return self._last_metrics or ExecutionMetrics(
            agent_type="compositional",
            execution_time=0.0,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=0,
            tool_calls_count=0,
        )
