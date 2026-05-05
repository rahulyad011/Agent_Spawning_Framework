"""Orchestrator for meta-agent."""

import time
from dataclasses import dataclass
from typing import Dict, Tuple

from runtime_agents.shared.base import BaseOrchestrator, ExecutionMetrics
from runtime_agents.shared.llm import LLMClient
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

from .meta_agent import MetaAgent
from .prompt_builder import DynamicPromptBuilder
from .tool_selector import DynamicToolSelector

logger = get_logger(__name__)


@dataclass
class MetaOrchestrator(BaseOrchestrator):
    """Orchestrator for single adaptive meta-agent."""

    available_tools: Dict[str, Tool]
    _last_metrics: ExecutionMetrics = None

    def __init__(
        self,
        llm: LLMClient,
        available_tools: Dict[str, Tool],
        session_context: str = "",
    ):
        super().__init__(llm, session_context)
        self.available_tools = available_tools
        self.prompt_builder = DynamicPromptBuilder(llm)
        self.tool_selector = DynamicToolSelector(llm, available_tools)
        self.meta_agent = MetaAgent(
            llm=llm,
            available_tools=available_tools,
            prompt_builder=self.prompt_builder,
            tool_selector=self.tool_selector,
        )

    async def run(self, requirement: str) -> Tuple[list, str]:
        """Run the meta-agent."""
        start_time = time.time()
        logger.info(f"[META_ORCH] Starting execution for: {requirement[:100]}...")

        # Execute meta-agent
        result = await self.meta_agent.run(requirement, context=self.session_context)
        results = [result]
        final = result.output

        execution_time = time.time() - start_time
        self._last_metrics = ExecutionMetrics(
            agent_type="meta",
            execution_time=execution_time,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=1,
            tool_calls_count=len(result.tool_calls),
        )

        logger.info(f"[META_ORCH] Execution complete in {execution_time:.2f}s")
        return results, final

    def get_metrics(self) -> ExecutionMetrics:
        """Get performance metrics."""
        return self._last_metrics or ExecutionMetrics(
            agent_type="meta",
            execution_time=0.0,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=0,
            tool_calls_count=0,
        )
