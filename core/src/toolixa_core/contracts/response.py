"""Structured, serializable results returned by agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_APPROVAL = "needs_approval"


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Workspace-relative reference to an output artifact."""

    path: str
    media_type: str = "application/octet-stream"

    def __post_init__(self) -> None:
        if not self.path or self.path.startswith(("/", "\\")):
            raise ValueError("artifact path must be a non-empty relative path")
        if ".." in self.path.replace("\\", "/").split("/"):
            raise ValueError("artifact path cannot traverse parent directories")


@dataclass(frozen=True, slots=True)
class AgentResult:
    request_id: str
    agent_id: str
    status: AgentStatus
    output: dict[str, Any] = field(default_factory=dict)
    artifacts: tuple[ArtifactReference, ...] = ()
    usage: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, AgentStatus):
            raise TypeError("status must be an AgentStatus value")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result
