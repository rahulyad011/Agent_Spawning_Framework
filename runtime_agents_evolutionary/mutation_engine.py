"""Mutation and crossover for evolutionary system."""

import random
from dataclasses import dataclass
from typing import List

from runtime_agents.shared.logger import get_logger

from .agent_pool import AgentConfig

logger = get_logger(__name__)


class MutationEngine:
    """Engine for mutating and crossing over agent configurations."""

    def __init__(self, mutation_rate: float = 0.1, crossover_rate: float = 0.7):
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate

    def mutate(self, config: AgentConfig, available_tools: List[str]) -> AgentConfig:
        """Mutate an agent configuration."""
        logger.debug(f"[MUTATION] Mutating config {config.config_id}")

        # Mutate prompt
        prompt_variations = [
            config.system_prompt + " Be thorough.",
            config.system_prompt + " Be concise.",
            config.system_prompt.replace("You are", "You are an expert"),
        ]
        new_prompt = random.choice(prompt_variations) if random.random() < self.mutation_rate else config.system_prompt

        # Mutate tools
        new_tools = config.tool_names.copy()
        if random.random() < self.mutation_rate:
            if random.random() < 0.5 and new_tools:
                # Remove a tool
                new_tools.remove(random.choice(new_tools))
            else:
                # Add a tool
                available = [t for t in available_tools if t not in new_tools]
                if available:
                    new_tools.append(random.choice(available))

        return AgentConfig(
            config_id=f"{config.config_id}_mutated",
            system_prompt=new_prompt,
            tool_names=new_tools,
        )

    def crossover(self, config1: AgentConfig, config2: AgentConfig) -> AgentConfig:
        """Create new config by crossing over two configs."""
        logger.debug(f"[MUTATION] Crossing over {config1.config_id} and {config2.config_id}")

        # Crossover prompt (take from one parent)
        new_prompt = config1.system_prompt if random.random() < 0.5 else config2.system_prompt

        # Crossover tools (merge both sets)
        new_tools = list(set(config1.tool_names + config2.tool_names))

        return AgentConfig(
            config_id=f"{config1.config_id}_x_{config2.config_id}",
            system_prompt=new_prompt,
            tool_names=new_tools,
        )

    def evolve_pool(
        self, pool: List[AgentConfig], available_tools: List[str], num_offspring: int = 2
    ) -> List[AgentConfig]:
        """Evolve the pool by mutation and crossover."""
        new_configs = []

        # Select top performers for breeding
        sorted_pool = sorted(pool, key=lambda x: x.fitness_score, reverse=True)
        top_performers = sorted_pool[:len(sorted_pool) // 2]

        # Create offspring through crossover
        for _ in range(num_offspring):
            if len(top_performers) >= 2:
                parent1, parent2 = random.sample(top_performers, 2)
                if random.random() < self.crossover_rate:
                    offspring = self.crossover(parent1, parent2)
                    new_configs.append(offspring)

        # Mutate some configs
        for config in random.sample(pool, min(len(pool) // 4, 3)):
            if random.random() < self.mutation_rate:
                mutated = self.mutate(config, available_tools)
                new_configs.append(mutated)

        logger.info(f"[MUTATION] Created {len(new_configs)} new configurations")
        return new_configs
