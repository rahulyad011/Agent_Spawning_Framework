"""Performance tracking and metrics collection for agent architectures."""

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from runtime_agents.shared.base import ExecutionMetrics


class PerformanceTracker:
    """Tracks performance metrics for agent executions."""

    def __init__(self, metrics_file: str = "performance_metrics.json"):
        self.metrics_file = Path(metrics_file)
        self.metrics: List[ExecutionMetrics] = []
        self.current_execution_start: Optional[float] = None

    def start_execution(self) -> None:
        """Mark the start of an execution."""
        self.current_execution_start = time.time()

    def record_execution(
        self,
        agent_type: str,
        execution_time: float,
        token_usage: Dict[str, int],
        cost_estimate: float,
        num_agents_spawned: int,
        tool_calls_count: int,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> ExecutionMetrics:
        """Record execution metrics."""
        metrics = ExecutionMetrics(
            agent_type=agent_type,
            execution_time=execution_time,
            token_usage=token_usage,
            cost_estimate=cost_estimate,
            num_agents_spawned=num_agents_spawned,
            tool_calls_count=tool_calls_count,
            success=success,
            error_message=error_message,
        )
        self.metrics.append(metrics)
        return metrics

    def get_execution_time(self) -> float:
        """Get elapsed time since start_execution was called."""
        if self.current_execution_start is None:
            return 0.0
        return time.time() - self.current_execution_start

    def save_metrics(self) -> None:
        """Save metrics to file."""
        if not self.metrics:
            return

        data = {
            "last_updated": datetime.utcnow().isoformat(),
            "metrics": [asdict(m) for m in self.metrics],
        }

        with open(self.metrics_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_metrics(self) -> None:
        """Load metrics from file."""
        if not self.metrics_file.exists():
            return

        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.metrics = [
                    ExecutionMetrics(**m) for m in data.get("metrics", [])
                ]
        except Exception as e:
            print(f"Error loading metrics: {e}")

    def get_comparison_stats(self) -> Dict[str, Dict]:
        """Get comparison statistics grouped by agent type."""
        stats: Dict[str, List[ExecutionMetrics]] = {}
        for metric in self.metrics:
            if metric.agent_type not in stats:
                stats[metric.agent_type] = []
            stats[metric.agent_type].append(metric)

        comparison = {}
        for agent_type, metrics_list in stats.items():
            if not metrics_list:
                continue

            total_executions = len(metrics_list)
            avg_time = sum(m.execution_time for m in metrics_list) / total_executions
            avg_cost = sum(m.cost_estimate for m in metrics_list) / total_executions
            avg_agents = sum(m.num_agents_spawned for m in metrics_list) / total_executions
            success_rate = sum(1 for m in metrics_list if m.success) / total_executions

            total_input_tokens = sum(m.token_usage.get("input_tokens", 0) for m in metrics_list)
            total_output_tokens = sum(m.token_usage.get("output_tokens", 0) for m in metrics_list)

            comparison[agent_type] = {
                "total_executions": total_executions,
                "avg_execution_time": avg_time,
                "avg_cost": avg_cost,
                "avg_agents_spawned": avg_agents,
                "success_rate": success_rate,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
            }

        return comparison
