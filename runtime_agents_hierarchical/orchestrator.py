"""Orchestrator for hierarchical agents."""

import time
from dataclasses import dataclass
from typing import Dict, Tuple

from runtime_agents.shared.base import BaseOrchestrator, ExecutionMetrics
from runtime_agents.shared.llm import LLMClient
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

from .parent_agent import ParentAgent
from .task_decomposer import SubTask, TaskDecomposer

logger = get_logger(__name__)


@dataclass
class HierarchicalOrchestrator(BaseOrchestrator):
    """Orchestrator for hierarchical agent networks."""

    available_tools: Dict[str, Tool]
    max_depth: int = 3
    parallel_execution: bool = True
    _last_metrics: ExecutionMetrics = None

    def __init__(
        self,
        llm: LLMClient,
        available_tools: Dict[str, Tool],
        session_context: str = "",
        max_depth: int = 3,
        parallel_execution: bool = True,
    ):
        super().__init__(llm, session_context)
        self.available_tools = available_tools
        self.max_depth = max_depth
        self.parallel_execution = parallel_execution
        self.decomposer = TaskDecomposer(llm, max_depth)
        self.parent_agent = ParentAgent(llm, available_tools)

    async def run(self, requirement: str) -> Tuple[list, str]:
        """Run with hierarchical agent structure."""
        start_time = time.time()
        logger.info(f"[HIER_ORCH] Starting execution for: {requirement[:100]}...")

        # Decompose task
        sub_tasks = await self.decomposer.decompose(requirement)
        logger.info(f"[HIER_ORCH] Decomposed into {len(sub_tasks)} sub-tasks")

        if not sub_tasks:
            # No decomposition, execute directly
            from runtime_agents.shared.base import AgentResult
            from runtime_agents.shared.llm import Message

            messages = [
                Message("system", "You are a helpful assistant."),
                Message("user", requirement),
            ]
            output = await self.llm.chat(messages, temperature=0.2)
            result = AgentResult(agent_name="Root", output=output)
            final = output
            results = [result]
        else:
            # Execute children
            child_results = await self.parent_agent.spawn_and_execute_children(
                sub_tasks, context=self.session_context, parallel=self.parallel_execution
            )

            # Aggregate results
            context = "\n\n".join([f"[{r.agent_name}]\n{r.output}" for r in child_results])
            agg_prompt = (
                "You are an aggregator. Produce the best final answer using the sub-task results below.\n"
                + context
            )
            from runtime_agents.shared.llm import Message

            final = await self.llm.chat(
                [Message("system", agg_prompt), Message("user", "Return the final answer.")],
                temperature=0.2,
            )
            results = child_results

        execution_time = time.time() - start_time
        self._last_metrics = ExecutionMetrics(
            agent_type="hierarchical",
            execution_time=execution_time,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=len(sub_tasks) if sub_tasks else 1,
            tool_calls_count=sum(len(r.tool_calls) for r in results),
        )

        logger.info(f"[HIER_ORCH] Execution complete in {execution_time:.2f}s")
        return results, final

    def get_metrics(self) -> ExecutionMetrics:
        """Get performance metrics."""
        return self._last_metrics or ExecutionMetrics(
            agent_type="hierarchical",
            execution_time=0.0,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=0,
            tool_calls_count=0,
        )
