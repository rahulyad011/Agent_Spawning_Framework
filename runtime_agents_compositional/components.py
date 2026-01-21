"""Reusable agent components for compositional building."""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AgentComponent:
    """Reusable agent building block."""

    skill: str  # e.g., "data_analysis", "web_research"
    behavior: str  # e.g., "thorough", "quick", "creative"
    system_prompt_template: str
    tool_names: List[str] = field(default_factory=list)
    description: str = ""


class ComponentLibrary:
    """Library of reusable agent components."""

    def __init__(self):
        self._components: Dict[str, AgentComponent] = {}
        self._initialize_default_components()

    def _initialize_default_components(self):
        """Initialize default component library."""
        components = [
            AgentComponent(
                skill="data_analysis",
                behavior="thorough",
                system_prompt_template="You are a data analyst. {behavior_instruction} Analyze data, identify patterns, and provide insights.",
                tool_names=["file_read", "db_query"],
                description="Analyzes data and identifies patterns",
            ),
            AgentComponent(
                skill="web_research",
                behavior="thorough",
                system_prompt_template="You are a researcher. {behavior_instruction} Gather information from web sources and provide factual details.",
                tool_names=["http_get"],
                description="Gathers information from web sources",
            ),
            AgentComponent(
                skill="writing",
                behavior="creative",
                system_prompt_template="You are a writer. {behavior_instruction} Write clear, engaging content tailored to the audience.",
                tool_names=["file_read"],
                description="Creates written content",
            ),
            AgentComponent(
                skill="planning",
                behavior="thorough",
                system_prompt_template="You are a planner. {behavior_instruction} Break down tasks into actionable steps.",
                tool_names=["time_now"],
                description="Creates execution plans",
            ),
        ]

        for comp in components:
            self._components[comp.skill] = comp

    def get_component(self, skill: str) -> AgentComponent:
        """Get a component by skill name."""
        return self._components.get(skill)

    def list_skills(self) -> List[str]:
        """List all available skills."""
        return list(self._components.keys())

    def add_component(self, component: AgentComponent) -> None:
        """Add a new component to the library."""
        self._components[component.skill] = component
