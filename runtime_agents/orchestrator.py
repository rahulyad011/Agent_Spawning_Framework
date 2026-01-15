from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .agents import AgentInstance, AgentResult, AgentTemplate
from .llm import LLMClient, Message
from .tools import Tool


@dataclass
class Orchestrator:
    """Routes a request to a set of agent templates, spawns instances, runs them, aggregates.

    This starter uses:
    - LLM-based router (with heuristic fallback)
    - sequential execution (easy to extend to parallel)
    - a final aggregation prompt
    """

    llm: LLMClient
    registry: Dict[str, AgentTemplate]
    tools: Dict[str, Tool]

    async def _route(self, requirement: str) -> List[str]:
        """Return a list of template keys to run for this request."""
        router_prompt = (
            "You are a router. Pick which agent roles to run for the user request.\n"
            "Available agents:\n"
            + "\n".join([f"- {k}: {t.name}" for k, t in self.registry.items()])
            + "\n\nReturn ONLY a comma-separated list of agent keys (e.g., planner,researcher)."
        )

        try:
            out = await self.llm.chat(
                [Message("system", router_prompt), Message("user", requirement)],
                temperature=0.0,
            )
            keys = [k.strip() for k in out.split(",") if k.strip()]
            keys = [k for k in keys if k in self.registry]
            if keys:
                return keys
        except Exception:
            # Router failures should not break the whole run.
            pass

        # fallback heuristic
        req = requirement.lower()
        keys: List[str] = []
        if any(w in req for w in ["summarize", "rewrite", "draft", "email", "proposal"]):
            keys.append("writer")
        if any(w in req for w in ["analyze", "trend", "compare", "insight", "tradeoff"]):
            keys.append("analyst")
        if any(w in req for w in ["find", "search", "look up", "reference", "cite"]):
            keys.append("researcher")
        if not keys:
            keys = ["planner"]
        return keys

    def _spawn(self, key: str) -> AgentInstance:
        template = self.registry[key]
        scoped_tools = {name: self.tools[name] for name in template.tool_names if name in self.tools}
        return AgentInstance(template=template, llm=self.llm, tools=scoped_tools)

    async def run(self, requirement: str) -> Tuple[List[AgentResult], str]:
        """Run a request end-to-end."""
        plan = await self._route(requirement)
        results: List[AgentResult] = []

        context = ""
        for key in plan:
            agent = self._spawn(key)
            res = await agent.run(requirement, context=context if context else None)
            results.append(res)
            context += f"\n\n[{res.agent_name}]\n{res.output}"

        agg_prompt = (
            "You are an aggregator. Produce the best final answer using the agent outputs below.\n"
            + context
        )
        final = await self.llm.chat(
            [Message("system", agg_prompt), Message("user", "Return the final answer." )],
            temperature=0.2,
        )

        return results, final
