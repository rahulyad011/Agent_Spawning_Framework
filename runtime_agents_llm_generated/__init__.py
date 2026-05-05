"""LLM-generated agent architecture."""

from .generator import DynamicAgentGenerator
from .orchestrator import LLMGeneratedOrchestrator

__all__ = ["LLMGeneratedOrchestrator", "DynamicAgentGenerator"]
