"""Orchestrator for LLM-generated agents."""

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from runtime_agents.shared.base import BaseOrchestrator, ExecutionMetrics
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

from .generator import AgentSpec, DynamicAgentGenerator

logger = get_logger(__name__)


@dataclass
class LLMAgentInstance:
    """Instance of an LLM-generated agent."""

    spec: AgentSpec
    llm: LLMClient
    tools: Dict[str, Tool]

    async def run(self, user_input: str, *, context: Optional[str] = None):
        """Run the agent."""
        from runtime_agents.shared.base import AgentResult

        sys_prompt = self.spec.system_prompt
        if context:
            sys_prompt += f"\n\nContext:\n{context}"

        tool_catalog = "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
        sys_prompt += f"\n\nAvailable tools:\n{tool_catalog}"

        messages = [
            Message("system", sys_prompt),
            Message("user", user_input),
        ]

        output = await self.llm.chat(messages, temperature=0.2)
        return AgentResult(agent_name=self.spec.name, output=output)


@dataclass
class LLMGeneratedOrchestrator(BaseOrchestrator):
    """Orchestrator that generates agents dynamically using LLM."""

    available_tools: Dict[str, Tool]
    max_agents: int = 3
    temperature: float = 0.7
    _last_metrics: ExecutionMetrics = None

    def __init__(self, llm: LLMClient, available_tools: Dict[str, Tool], session_context: str = "", max_agents: int = 3, temperature: float = 0.7):
        super().__init__(llm, session_context)
        self.available_tools = available_tools
        self.max_agents = max_agents
        self.temperature = temperature
        self.generator = DynamicAgentGenerator(llm, available_tools, temperature)

    async def run(self, requirement: str) -> Tuple[List, str]:
        """Run with dynamically generated agents."""
        start_time = time.time()
        logger.info(f"[LLM_ORCH] Starting execution for: {requirement[:100]}...")

        # Generate agent specs
        specs = await self.generator.generate_agent_spec(requirement, self.max_agents)
        logger.info(f"[LLM_ORCH] Generated {len(specs)} agent specs")

        results = []
        context = self.session_context

        # Execute each generated agent
        for idx, spec in enumerate(specs, 1):
            logger.info(f"[LLM_ORCH] Executing agent {idx}/{len(specs)}: {spec.name}")
            scoped_tools = {
                name: self.available_tools[name]
                for name in spec.tool_names
                if name in self.available_tools
            }
            agent = LLMAgentInstance(spec=spec, llm=self.llm, tools=scoped_tools)
            res = await agent.run(requirement, context=context if context else None)
            results.append(res)
            context += f"\n\n[{res.agent_name}]\n{res.output}"

        # Aggregate results
        logger.info("[LLM_ORCH] Aggregating results...")
        agg_prompt = (
            "You are an aggregator. Produce the best final answer using the agent outputs below.\n"
            + context
        )
        final = await self.llm.chat(
            [Message("system", agg_prompt), Message("user", "Return the final answer.")],
            temperature=0.2,
        )

        execution_time = time.time() - start_time
        self._last_metrics = ExecutionMetrics(
            agent_type="llm_generated",
            execution_time=execution_time,
            token_usage={"input_tokens": 0, "output_tokens": 0},  # Would track actual usage
            cost_estimate=0.0,  # Would calculate based on tokens
            num_agents_spawned=len(specs),
            tool_calls_count=sum(len(r.tool_calls) for r in results),
        )

        logger.info(f"[LLM_ORCH] Execution complete in {execution_time:.2f}s")
        return results, final

    def get_metrics(self) -> ExecutionMetrics:
        """Get performance metrics."""
        return self._last_metrics or ExecutionMetrics(
            agent_type="llm_generated",
            execution_time=0.0,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=0,
            tool_calls_count=0,
        )
