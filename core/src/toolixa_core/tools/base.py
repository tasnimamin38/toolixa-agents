"""Tool metadata and execution context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from toolixa_core.security.policy import RuntimePolicy


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    required_permissions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tool name cannot be empty")


@dataclass(frozen=True, slots=True)
class ToolCallContext:
    request_id: str
    trace_id: str
    workspace: Path | None
    policy: RuntimePolicy


class Tool(Protocol):
    spec: ToolSpec

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        """Perform one bounded operation after policy checks."""
        ...
