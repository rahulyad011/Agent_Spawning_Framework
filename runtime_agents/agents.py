from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .llm import LLMClient, Message
from .tools import Tool


class AgentResult(BaseModel):
    agent_name: str
    output: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


@dataclass(frozen=True)
class AgentTemplate:
    """A versionable, pre-approved agent spec.

    In production, keep templates in source control (and ideally version them).
    """

    key: str
    name: str
    system_prompt: str
    tool_names: List[str]


@dataclass
class AgentInstance:
    """A runtime-spawned instance created from an AgentTemplate."""

    template: AgentTemplate
    llm: LLMClient
    tools: Dict[str, Tool]  # scoped toolset

    async def run(self, user_input: str, *, context: Optional[str] = None) -> AgentResult:
        sys = self.template.system_prompt
        if context:
            sys += "\n\nContext (from other agents):\n" + context

        tool_catalog = "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])
        sys += "\n\nAvailable tools:\n" + (tool_catalog if tool_catalog else "- (none)")

        messages = [
            Message(role="system", content=sys),
            Message(role="user", content=user_input),
        ]

        text = await self.llm.chat(messages, temperature=0.2)

        # This starter does not auto-execute tool calls.
        # Next step: parse a JSON tool-call schema, execute tools, then continue.
        return AgentResult(agent_name=self.template.name, output=text)
