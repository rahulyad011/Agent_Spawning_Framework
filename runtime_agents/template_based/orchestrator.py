from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from runtime_agents.shared.base import BaseOrchestrator, ExecutionMetrics
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

from runtime_agents.shared.base import AgentResult

from .agents import AgentInstance, AgentTemplate

logger = get_logger(__name__)


@dataclass
class Orchestrator(BaseOrchestrator):
    """Routes a request to a set of agent templates, spawns instances, runs them, aggregates.

    This starter uses:
    - LLM-based router (with heuristic fallback)
    - sequential execution (easy to extend to parallel)
    - a final aggregation prompt
    """

    llm: LLMClient
    registry: Dict[str, AgentTemplate]
    tools: Dict[str, Tool]
    session_context: str = ""  # Additional context about session resources

    async def _route(self, requirement: str) -> List[str]:
        """Return a list of template keys to run for this request."""
        logger.debug(f"[ROUTER] Starting routing for requirement: {requirement[:100]}...")
        logger.debug(f"[ROUTER] Available agents: {list(self.registry.keys())}")
        
        router_prompt = (
            "You are a router. Pick which agent roles to run for the user request.\n"
            "Available agents:\n"
            + "\n".join([f"- {k}: {t.name}" for k, t in self.registry.items()])
            + "\n\nReturn ONLY a comma-separated list of agent keys (e.g., planner,researcher)."
        )

        try:
            logger.debug("[ROUTER] Attempting LLM-based routing...")
            out = await self.llm.chat(
                [Message("system", router_prompt), Message("user", requirement)],
                temperature=0.0,
            )
            logger.debug(f"[ROUTER] LLM routing response: {out}")
            keys = [k.strip() for k in out.split(",") if k.strip()]
            keys = [k for k in keys if k in self.registry]
            if keys:
                logger.info(f"[ROUTER] Selected agents via LLM: {keys}")
                return keys
            else:
                logger.debug("[ROUTER] LLM returned invalid keys, falling back to heuristics")
        except Exception as e:
            logger.warning(f"[ROUTER] LLM routing failed: {e}, falling back to heuristics")

        # fallback heuristic
        logger.debug("[ROUTER] Using heuristic fallback routing")
        req = requirement.lower()
        keys: List[str] = []
        if any(w in req for w in ["summarize", "rewrite", "draft", "email", "proposal"]):
            keys.append("writer")
            logger.debug("[ROUTER] Heuristic: Added 'writer' agent")
        if any(w in req for w in ["analyze", "trend", "compare", "insight", "tradeoff"]):
            keys.append("analyst")
            logger.debug("[ROUTER] Heuristic: Added 'analyst' agent")
        if any(w in req for w in ["find", "search", "look up", "reference", "cite"]):
            keys.append("researcher")
            logger.debug("[ROUTER] Heuristic: Added 'researcher' agent")
        if not keys:
            keys = ["planner"]
            logger.debug("[ROUTER] Heuristic: Defaulting to 'planner' agent")
        
        logger.info(f"[ROUTER] Final selected agents: {keys}")
        return keys

    def _spawn(self, key: str) -> AgentInstance:
        template = self.registry[key]
        scoped_tools = {name: self.tools[name] for name in template.tool_names if name in self.tools}
        logger.debug(f"[SPAWN] Spawning agent '{key}' ({template.name}) with tools: {list(scoped_tools.keys())}")
        return AgentInstance(template=template, llm=self.llm, tools=scoped_tools)

    async def run(self, requirement: str) -> Tuple[List[AgentResult], str]:
        """Run a request end-to-end."""
        logger.info(f"[ORCHESTRATOR] Starting execution for requirement: {requirement[:100]}...")
        logger.debug(f"[ORCHESTRATOR] Session context length: {len(self.session_context)} chars")
        
        plan = await self._route(requirement)
        logger.info(f"[ORCHESTRATOR] Execution plan: {plan}")
        
        results: List[AgentResult] = []

        context = ""
        for idx, key in enumerate(plan, 1):
            logger.info(f"[ORCHESTRATOR] Executing agent {idx}/{len(plan)}: {key}")
            agent = self._spawn(key)
            # Combine agent context with session context
            full_context = self.session_context
            if context:
                full_context = (full_context + "\n\n" + context) if full_context else context
            logger.debug(f"[ORCHESTRATOR] Passing context to agent (length: {len(full_context) if full_context else 0} chars)")
            
            res = await agent.run(requirement, context=full_context if full_context else None)
            logger.info(f"[ORCHESTRATOR] Agent '{key}' completed. Output length: {len(res.output)} chars")
            logger.debug(f"[ORCHESTRATOR] Agent '{key}' output: {res.output[:200]}...")
            
            results.append(res)
            context += f"\n\n[{res.agent_name}]\n{res.output}"

        logger.info("[ORCHESTRATOR] All agents completed, aggregating results...")
        agg_prompt = (
            "You are an aggregator. Produce the best final answer using the agent outputs below.\n"
            + context
        )
        final = await self.llm.chat(
            [Message("system", agg_prompt), Message("user", "Return the final answer." )],
            temperature=0.2,
        )
        logger.info(f"[ORCHESTRATOR] Aggregation complete. Final answer length: {len(final)} chars")

        return results, final

    def get_metrics(self) -> ExecutionMetrics:
        """Get performance metrics for the last execution."""
        # This would be populated during execution
        # For now, return a placeholder
        return ExecutionMetrics(
            agent_type="template_based",
            execution_time=0.0,
            token_usage={"input_tokens": 0, "output_tokens": 0},
            cost_estimate=0.0,
            num_agents_spawned=0,
            tool_calls_count=0,
        )
