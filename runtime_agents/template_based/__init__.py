"""Template-based agent architecture."""

from .agents import AgentInstance, AgentResult, AgentTemplate
from .orchestrator import Orchestrator

__all__ = ["Orchestrator", "AgentTemplate", "AgentInstance", "AgentResult"]
