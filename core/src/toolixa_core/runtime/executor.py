"""Executor protocol with a safe default that never launches commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    argv: tuple[str, ...]
    working_directory: str
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.argv or any(not part for part in self.argv):
            raise ValueError("argv must contain non-empty arguments")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


class Executor(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...


class ExecutionDisabled(PermissionError):
    pass


class DisabledExecutor:
    """Safe default: execution is unavailable until a separately reviewed adapter is configured."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        del request
        raise ExecutionDisabled("process execution is disabled; configure an isolated executor")