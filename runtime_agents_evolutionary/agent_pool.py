"""Agent pool for evolutionary system."""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from runtime_agents.shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentConfig:
    """Agent configuration in the pool."""

    config_id: str
    system_prompt: str
    tool_names: List[str]
    fitness_score: float = 0.0
    execution_count: int = 0
    success_count: int = 0


class AgentPool:
    """Maintains population of agent configurations."""

    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.pool: List[AgentConfig] = []
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize pool with random configurations."""
        base_prompts = [
            "You are a helpful assistant.",
            "You are a data analyst.",
            "You are a researcher.",
            "You are a writer.",
        ]
        base_tools = [
            ["file_read"],
            ["http_get"],
            ["file_read", "db_query"],
            ["time_now"],
        ]

        for i in range(self.pool_size):
            prompt = random.choice(base_prompts)
            tools = random.choice(base_tools)
            config = AgentConfig(
                config_id=f"config_{i}",
                system_prompt=prompt,
                tool_names=tools,
            )
            self.pool.append(config)

        logger.info(f"[POOL] Initialized pool with {len(self.pool)} configurations")

    def select_best(self, requirement: str, top_k: int = 3) -> List[AgentConfig]:
        """Select best configurations (fitness-based or similarity-based)."""
        # Sort by fitness score
        sorted_pool = sorted(self.pool, key=lambda x: x.fitness_score, reverse=True)
        return sorted_pool[:top_k]

    def select_similar(self, requirement: str, top_k: int = 3) -> List[AgentConfig]:
        """Select configurations similar to requirement (simple keyword matching)."""
        req_lower = requirement.lower()
        scored = []

        for config in self.pool:
            score = 0.0
            # Check if prompt keywords match requirement
            prompt_lower = config.system_prompt.lower()
            if any(word in prompt_lower for word in req_lower.split()):
                score += 0.5
            # Fitness bonus
            score += config.fitness_score * 0.5
            scored.append((score, config))

        scored.sort(reverse=True)
        return [config for _, config in scored[:top_k]]

    def add_config(self, config: AgentConfig) -> None:
        """Add a new configuration to the pool."""
        self.pool.append(config)
        # Keep pool size constant
        if len(self.pool) > self.pool_size:
            # Remove lowest fitness
            self.pool.sort(key=lambda x: x.fitness_score)
            self.pool.pop(0)

    def update_fitness(self, config_id: str, success: bool) -> None:
        """Update fitness score for a configuration."""
        for config in self.pool:
            if config.config_id == config_id:
                config.execution_count += 1
                if success:
                    config.success_count += 1
                # Calculate fitness as success rate
                config.fitness_score = config.success_count / config.execution_count if config.execution_count > 0 else 0.0
                logger.debug(f"[POOL] Updated fitness for {config_id}: {config.fitness_score}")
                break
