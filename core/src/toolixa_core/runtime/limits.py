"""Monotonic execution budget tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass

from toolixa_core.contracts.request import ExecutionBudget


class BudgetExceeded(RuntimeError):
    """Raised when a request exceeds an explicit execution budget."""


@dataclass(slots=True)
class BudgetTracker:
    budget: ExecutionBudget
    started_at: float = 0.0
    steps: int = 0
    tool_calls: int = 0

    def __post_init__(self) -> None:
        if self.started_at == 0.0:
            self.started_at = time.monotonic()

    def step(self) -> None:
        self.steps += 1
        self.check()

    def tool_call(self) -> None:
        self.tool_calls += 1
        self.check()

    def check(self) -> None:
        if self.steps > self.budget.max_steps:
            raise BudgetExceeded("maximum step count exceeded")
        if self.tool_calls > self.budget.max_tool_calls:
            raise BudgetExceeded("maximum tool-call count exceeded")
        if time.monotonic() - self.started_at > self.budget.max_wall_seconds:
            raise BudgetExceeded("maximum wall-time budget exceeded")
