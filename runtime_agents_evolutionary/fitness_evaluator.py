"""Fitness evaluation for evolutionary system."""

from dataclasses import dataclass
from typing import Optional

from runtime_agents.shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FitnessResult:
    """Result of fitness evaluation."""

    fitness_score: float
    success: bool
    execution_time: float
    quality_score: float = 0.0  # Subjective quality (0-1)


class FitnessEvaluator:
    """Evaluates fitness of agent configurations."""

    def __init__(self, fitness_threshold: float = 0.7):
        self.fitness_threshold = fitness_threshold

    def evaluate(
        self,
        execution_time: float,
        success: bool,
        quality_score: Optional[float] = None,
    ) -> FitnessResult:
        """Evaluate fitness based on execution metrics."""
        # Simple fitness: success + quality + speed bonus
        fitness = 0.0

        if success:
            fitness += 0.5

        if quality_score is not None:
            fitness += quality_score * 0.3
        else:
            # Assume good quality if successful
            fitness += 0.3 if success else 0.0

        # Speed bonus (faster is better, normalized)
        speed_bonus = max(0, 0.2 * (1.0 - min(execution_time / 60.0, 1.0)))
        fitness += speed_bonus

        result = FitnessResult(
            fitness_score=fitness,
            success=success,
            execution_time=execution_time,
            quality_score=quality_score or (0.8 if success else 0.2),
        )

        logger.debug(f"[FITNESS] Evaluated fitness: {fitness:.2f}")
        return result
