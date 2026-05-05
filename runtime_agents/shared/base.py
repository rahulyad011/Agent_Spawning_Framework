"""Base classes and interfaces for all agent architectures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Shared result structure for all agent types."""

    agent_name: str
    output: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time: float = 0.0  # seconds
    token_usage: Optional[Dict[str, int]] = None  # input_tokens, output_tokens


@dataclass
class ExecutionMetrics:
    """Performance metrics for agent execution."""

    agent_type: str
    execution_time: float  # seconds
    token_usage: Dict[str, int]  # input_tokens, output_tokens
    cost_estimate: float  # USD
    num_agents_spawned: int
    tool_calls_count: int
    success: bool = True
    error_message: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all agent implementations."""

    @abstractmethod
    async def run(self, user_input: str, *, context: Optional[str] = None) -> AgentResult:
        """Execute the agent with given input and context."""
        pass


class BaseOrchestrator(ABC):
    """Abstract base class for all orchestrator implementations."""

    def __init__(self, llm, session_context: str = ""):
        self.llm = llm
        self.session_context = session_context

    @abstractmethod
    async def run(self, requirement: str) -> Tuple[List[AgentResult], str]:
        """
        Execute the orchestrator with a user requirement.
        
        Returns:
            Tuple of (list of agent results, final aggregated answer)
        """
        pass

    @abstractmethod
    def get_metrics(self) -> ExecutionMetrics:
        """Get performance metrics for the last execution."""
        pass
