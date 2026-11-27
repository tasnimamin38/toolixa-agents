"""Request and budget contracts shared by Toolixa agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ExecutionBudget:
    """Hard upper bounds an agent should enforce for one request."""

    max_steps: int = 25
    max_tool_calls: int = 20
    max_wall_seconds: float = 120.0

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if self.max_tool_calls < 0:
            raise ValueError("max_tool_calls cannot be negative")
        if self.max_wall_seconds <= 0:
            raise ValueError("max_wall_seconds must be positive")


@dataclass(frozen=True, slots=True)
class AgentRequest:
    """A provider-neutral request; grants are inputs, not self-issued permissions."""

    agent_id: str
    input: dict[str, Any]
    workspace: str | None = None
    grants: frozenset[str] = field(default_factory=frozenset)
    budget: ExecutionBudget = field(default_factory=ExecutionBudget)
    request_id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id cannot be empty")
        if not isinstance(self.input, dict):
            raise TypeError("input must be a dictionary")
        if any(not isinstance(item, str) for item in self.grants):
            raise TypeError("grants must contain strings")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation without secrets or runtime objects."""
        return {
            "agent_id": self.agent_id,
            "input": self.input,
            "workspace": self.workspace,
            "grants": sorted(self.grants),
            "budget": asdict(self.budget),
            "request_id": self.request_id,
            "trace_id": self.trace_id,
        }
