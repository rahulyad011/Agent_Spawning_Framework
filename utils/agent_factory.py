"""Factory for creating orchestrators based on configuration."""

import yaml
from pathlib import Path
from typing import Dict, Optional

from runtime_agents.shared.base import BaseOrchestrator
from runtime_agents.shared.llm import LLMClient
from runtime_agents.shared.tools import Tool

from runtime_agents.template_based.orchestrator import Orchestrator as TemplateOrchestrator
from runtime_agents_llm_generated import LLMGeneratedOrchestrator
from runtime_agents_compositional import CompositionalOrchestrator
from runtime_agents_meta import MetaOrchestrator
from runtime_agents_hierarchical import HierarchicalOrchestrator
from runtime_agents_evolutionary import EvolutionaryOrchestrator


class AgentFactory:
    """Factory for creating agent orchestrators."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            return {"agent_type": "template_based"}

        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {"agent_type": "template_based"}

    def create_orchestrator(
        self,
        llm: LLMClient,
        tools: Dict[str, Tool],
        session_context: str = "",
        agent_type: Optional[str] = None,
    ) -> BaseOrchestrator:
        """
        Create an orchestrator based on configuration.
        
        Args:
            llm: LLM client instance
            tools: Dictionary of available tools
            session_context: Session context string
            agent_type: Override agent type from config
        
        Returns:
            BaseOrchestrator instance
        """
        agent_type = agent_type or self.config.get("agent_type", "template_based")
        agent_config = self.config.get(agent_type, {})

        if agent_type == "template_based":
            # Need registry for template-based
            from runtime_agents.template_based.agents import AgentTemplate

            registry = {
                "planner": AgentTemplate(
                    key="planner",
                    name="Planner",
                    system_prompt="You break down the request into an execution plan and identify missing info.",
                    tool_names=["time_now", "file_list", "image_list"],
                ),
                "researcher": AgentTemplate(
                    key="researcher",
                    name="Researcher",
                    system_prompt=(
                        "You gather references and factual details. "
                        "If you need to fetch a URL, ask for it (or use http_get if available and appropriate)."
                    ),
                    tool_names=["http_get", "file_read"],
                ),
                "analyst": AgentTemplate(
                    key="analyst",
                    name="Analyst",
                    system_prompt="You analyze tradeoffs, compare options, and produce structured reasoning.",
                    tool_names=["file_read", "db_schema", "db_query"],
                ),
                "writer": AgentTemplate(
                    key="writer",
                    name="Writer",
                    system_prompt="You write clean, concise outputs tailored to the request.",
                    tool_names=["file_read"],
                ),
            }

            return TemplateOrchestrator(
                llm=llm,
                registry=registry,
                tools=tools,
                session_context=session_context,
            )

        elif agent_type == "llm_generated":
            return LLMGeneratedOrchestrator(
                llm=llm,
                available_tools=tools,
                session_context=session_context,
                max_agents=agent_config.get("max_agents", 3),
                temperature=agent_config.get("temperature", 0.7),
            )

        elif agent_type == "compositional":
            return CompositionalOrchestrator(
                llm=llm,
                available_tools=tools,
                session_context=session_context,
            )

        elif agent_type == "meta":
            return MetaOrchestrator(
                llm=llm,
                available_tools=tools,
                session_context=session_context,
            )

        elif agent_type == "hierarchical":
            return HierarchicalOrchestrator(
                llm=llm,
                available_tools=tools,
                session_context=session_context,
                max_depth=agent_config.get("max_depth", 3),
                parallel_execution=agent_config.get("parallel_execution", True),
            )

        elif agent_type == "evolutionary":
            return EvolutionaryOrchestrator(
                llm=llm,
                available_tools=tools,
                session_context=session_context,
                pool_size=agent_config.get("pool_size", 10),
                mutation_rate=agent_config.get("mutation_rate", 0.1),
                crossover_rate=agent_config.get("crossover_rate", 0.7),
                selection_method=agent_config.get("selection_method", "fitness_based"),
                fitness_threshold=agent_config.get("fitness_threshold", 0.7),
            )

        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
