"""Task decomposition for hierarchical agents."""

from dataclasses import dataclass
from typing import List

from runtime_agents.shared.llm import LLMClient, Message
from runtime_agents.shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SubTask:
    """A sub-task in the decomposition."""

    description: str
    dependencies: List[str] = None  # IDs of tasks this depends on
    task_id: str = ""


class TaskDecomposer:
    """Decomposes complex tasks into sub-tasks."""

    def __init__(self, llm: LLMClient, max_depth: int = 3):
        self.llm = llm
        self.max_depth = max_depth

    async def decompose(self, task: str, depth: int = 0) -> List[SubTask]:
        """Decompose a task into sub-tasks."""
        if depth >= self.max_depth:
            return []

        logger.debug(f"[DECOMPOSER] Decomposing task at depth {depth}")

        prompt = f"""Break down this task into 2-4 smaller sub-tasks:
{task}

Return a numbered list of sub-tasks. Each should be independent and actionable.
Format:
1. Sub-task 1
2. Sub-task 2
...
"""

        try:
            response = await self.llm.chat([Message("user", prompt)], temperature=0.3)
            # Parse numbered list
            lines = [line.strip() for line in response.split("\n") if line.strip()]
            sub_tasks = []
            for idx, line in enumerate(lines):
                # Remove numbering
                desc = line.split(". ", 1)[-1] if ". " in line else line
                if desc:
                    sub_tasks.append(SubTask(description=desc, task_id=f"task_{depth}_{idx}"))

            logger.debug(f"[DECOMPOSER] Created {len(sub_tasks)} sub-tasks")
            return sub_tasks
        except Exception as e:
            logger.warning(f"[DECOMPOSER] Error decomposing: {e}")
            return [SubTask(description=task, task_id="task_0_0")]
