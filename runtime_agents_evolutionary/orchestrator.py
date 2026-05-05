"""Orchestrator for evolutionary agents."""

import time
from dataclasses import dataclass
from typing import Dict, Tuple

from runtime_agents.shared.base import AgentResult, BaseOrchestrator, ExecutionMetrics
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

from .agent_pool import AgentConfig, AgentPool
from .fitness_evaluator import FitnessEvaluator
from .mutation_engine import MutationEngine

logger = get_logger(__name__)


@dataclass
class EvolutionaryAgentInstance:
    """Instance of an evolutionary agent."""

    config: AgentConfig
    llm: LLMClient
    tools: Dict[str, Tool]

    async def run(self, user_input: str, *, context: str = None) -> AgentResult:
        """Run the agent."""
        sys_prompt = self.config.system_prompt
        if context:
            sys_prompt += f"\n\nContext:\n{context}"

        tool_catalog = "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
        sys_prompt += f"\n\nAvailable tools:\n{tool_catalog}"

        messages = [
            Message("system", sys_prompt),
            Message("user", user_input),
        ]

        output = await self.llm.chat(messages, temperature=0.2)
        return AgentResult(agent_name=f"Evo-{self.config.config_id}", output=output)


@dataclass
class EvolutionaryOrchestrator(BaseOrchestrator):
    """Orchestrator for evolutionary agent system."""

    available_tools: Dict[str, Tool]
    pool_size: int = 10
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    selection_method: str = "fitness_based"
    fitness_threshold: float = 0.7
    _last_metrics: ExecutionMetrics = None

    def __init__(
        self,
        llm: LLMClient,
        available_tools: Dict[str, Tool],
        session_context: str = "",
        pool_size: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        selection_method: str = "fitness_based",
        fitness_threshold: float = 0.7,
    ):
        super().__init__(llm, session_context)
        self.available_tools = available_tools
        self.pool_size = pool_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.selection_method = selection_method
        self.fitness_threshold = fitness_threshold
        self.pool = AgentPool(pool_size)
        self.fitness_evaluator = FitnessEvaluator(fitness_threshold)
        self.mutation_engine = MutationEngine(mutation_rate, crossover_rate)

    async def run(self, requirement: str) -> Tuple[list, str]:
        """Run with evolutionary agent selection."""
        start_time = time.time()
        logger.info(f"[EVO_ORCH] Starting execution for: {requirement[:100]}...")

        # Select best config
        if self.selection_method == "similarity_based":
            selected_configs = self.pool.select_similar(requirement, top_k=1)
        else:
            selected_configs = self.pool.select_best(requirement, top_k=1)

        if not selected_configs:
            # Fallback
            selected_configs = [self.pool.pool[0]]

        config = selected_configs[0]
        logger.info(f"[EVO_ORCH] Selected config: {config.config_id} (fitness: {config.fitness_score:.2f})")

        # Create and execute agent
        scoped_tools = {
            name: self.available_tools[name]
            for name in config.tool_names
            if name in self.available_tools
        }
        agent = EvolutionaryAgentInstance(config=config, llm=self.llm, tools=scoped_tools)
        result = await agent.run(requirement, context=self.session_context)

        execution_time = time.time() - start_time

        # Evaluate fitness
        fitness_result = self.fitness_evaluator.evaluate(
            execution_time=execution_time,
            success=True,  # Would be determined by user feedback
            quality_score=None,
        )

        # Update pool fitness
        self.pool.update_fitness(config.config_id, fitness_result.success)

        # Evolve pool periodically (every 5 executions)
        if config.execution_count % 5 == 0:
            new_configs = self.mutation_engine.evolve_pool(
                self.pool.pool, list(self.available_tools.keys())
            )
            for new_config in new_configs:
                self.pool.add_config(new_config)

        results = [result]
        final = result.output

        self._last_metrics = ExecutionMetrics(
            agent_type="evolutionary",
            execution_time=execution_time,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=1,
            tool_calls_count=len(result.tool_calls),
        )

        logger.info(f"[EVO_ORCH] Execution complete in {execution_time:.2f}s")
        return results, final

    def get_metrics(self) -> ExecutionMetrics:
        """Get performance metrics."""
        return self._last_metrics or ExecutionMetrics(
            agent_type="evolutionary",
            execution_time=0.0,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=0,
            tool_calls_count=0,
        )
