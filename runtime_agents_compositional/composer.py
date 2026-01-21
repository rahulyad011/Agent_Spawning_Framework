"""Composition engine for building agents from components."""

from dataclasses import dataclass
from typing import Dict, List

from runtime_agents.shared.logger import get_logger

from .components import AgentComponent, ComponentLibrary

logger = get_logger(__name__)


@dataclass
class ComposedAgent:
    """An agent composed from components."""

    name: str
    system_prompt: str
    tool_names: List[str]
    components_used: List[str]


class CompositionEngine:
    """Engine for composing agents from components."""

    def __init__(self, component_library: ComponentLibrary):
        self.library = component_library

    def extract_skills(self, requirement: str) -> List[str]:
        """Extract needed skills from requirement (simple keyword matching)."""
        req_lower = requirement.lower()
        needed_skills = []

        skill_keywords = {
            "data_analysis": ["analyze", "data", "dataset", "statistics", "trend"],
            "web_research": ["find", "search", "look up", "research", "information"],
            "writing": ["write", "draft", "create", "compose", "summarize"],
            "planning": ["plan", "strategy", "steps", "break down", "organize"],
        }

        for skill, keywords in skill_keywords.items():
            if any(keyword in req_lower for keyword in keywords):
                needed_skills.append(skill)

        if not needed_skills:
            needed_skills = ["planning"]  # Default

        logger.debug(f"[COMPOSER] Extracted skills: {needed_skills}")
        return needed_skills

    def determine_behavior(self, requirement: str) -> str:
        """Determine behavior style from requirement."""
        req_lower = requirement.lower()
        if any(word in req_lower for word in ["quick", "fast", "brief"]):
            return "quick"
        elif any(word in req_lower for word in ["creative", "innovative", "novel"]):
            return "creative"
        else:
            return "thorough"

    def compose_agent(
        self, requirement: str, skills: List[str] = None, behavior: str = None
    ) -> ComposedAgent:
        """Compose an agent from components."""
        if skills is None:
            skills = self.extract_skills(requirement)
        if behavior is None:
            behavior = self.determine_behavior(requirement)

        components = [self.library.get_component(skill) for skill in skills if self.library.get_component(skill)]
        
        if not components:
            # Fallback to planning component
            components = [self.library.get_component("planning")]

        # Merge prompts
        behavior_instructions = {
            "thorough": "Be thorough and detailed in your analysis.",
            "quick": "Be concise and efficient.",
            "creative": "Be creative and think outside the box.",
        }
        behavior_instruction = behavior_instructions.get(behavior, behavior_instructions["thorough"])

        merged_prompt = "\n\n".join(
            [comp.system_prompt_template.format(behavior_instruction=behavior_instruction) for comp in components]
        )
        merged_prompt += f"\n\nYour task: {requirement}"

        # Merge tool names (unique)
        all_tools = set()
        for comp in components:
            all_tools.update(comp.tool_names)

        agent_name = " + ".join([comp.skill.replace("_", " ").title() for comp in components])

        logger.debug(f"[COMPOSER] Composed agent '{agent_name}' with tools: {list(all_tools)}")

        return ComposedAgent(
            name=agent_name,
            system_prompt=merged_prompt,
            tool_names=list(all_tools),
            components_used=[comp.skill for comp in components],
        )
