"""Orchestrator for LLM-generated agents."""

import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from runtime_agents.shared.base import BaseOrchestrator, ExecutionMetrics
from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger
from runtime_agents.shared.tools import Tool

from .generator import AgentSpec, DynamicAgentGenerator

logger = get_logger(__name__)


def _get_available_files_from_context(context: Optional[str]) -> List[str]:
    """Extract uploaded file names from session context (same pattern as template_based)."""
    if not context or "Uploaded files available:" not in context:
        return []
    file_pattern = re.compile(r"-\s+([^\s(]+\.(?:csv|txt|json|pdf|md|py|log|docx|xlsx))")
    return file_pattern.findall(context)


@dataclass
class LLMAgentInstance:
    """Instance of an LLM-generated agent."""

    spec: AgentSpec
    llm: LLMClient
    tools: Dict[str, Tool]

    async def run(self, user_input: str, *, context: Optional[str] = None):
        """Run the agent; when file_read is available and user asks for file analysis, run it and feed content to LLM."""
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
        tool_calls: List[Dict] = []
        tool_results: List[str] = []

        if "file_read" in self.tools and context:
            available = _get_available_files_from_context(context)
            user_lower = user_input.lower()
            analysis_keywords = ["analyze", "read", "examine", "look at", "check", "review", "process"]
            wants_analysis = any(kw in user_lower for kw in analysis_keywords)
            files_to_read: List[str] = []
            for filename in available:
                base = filename.split(".")[0].lower()
                if (
                    base in user_lower
                    or filename.lower() in user_lower
                    or (wants_analysis and len(available) == 1)
                    or ("file" in user_lower and len(available) == 1)
                    or ("dataset" in user_lower and filename.endswith(".csv"))
                ):
                    files_to_read.append(filename)
            for filename in files_to_read:
                try:
                    result = await self.tools["file_read"]({"filename": filename})
                    tool_calls.append({"tool": "file_read", "input": {"filename": filename}, "result": result})
                    content = result.get("content", "")
                    if result.get("type") == "csv":
                        content = (content or "")[:5000]
                    else:
                        content = (content or "")[:3000]
                    tool_results.append(f"File '{filename}' content:\n{content}")
                    logger.info(f"[LLM_AGENT:{self.spec.name}] Read file {filename} ({len(content)} chars)")
                except Exception as e:
                    logger.warning(f"[LLM_AGENT:{self.spec.name}] Error reading {filename}: {e}")
                    tool_calls.append({"tool": "file_read", "input": {"filename": filename}, "result": {"error": str(e)}})
                    tool_results.append(f"Error reading '{filename}': {str(e)}")

        if tool_results:
            follow_up = messages + [
                Message("assistant", output),
                Message(
                    "user",
                    "Here is the data from the tools I executed:\n\n"
                    + "\n\n".join(tool_results)
                    + "\n\nPlease analyze this data and provide your comprehensive answer based on the actual file contents.",
                ),
            ]
            output = await self.llm.chat(follow_up, temperature=0.2)
            logger.info(f"[LLM_AGENT:{self.spec.name}] Produced answer after file_read (length: {len(output)} chars)")

        return AgentResult(agent_name=self.spec.name, output=output, tool_calls=tool_calls)


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
