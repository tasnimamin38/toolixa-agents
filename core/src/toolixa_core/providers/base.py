"""Vendor-neutral provider protocol; concrete SDKs remain optional."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    provider: str
    model: str
    usage: dict[str, int]


class ProviderError(RuntimeError):
    """A bounded, user-safe provider failure."""


class ProviderAdapter(Protocol):
    name: str

    def generate(self, *, prompt: str, model: str, timeout_seconds: float) -> ModelResponse:
        """Generate text with a finite timeout and return structured usage."""
        ...


class ProviderRegistry:
    """Explicit provider registry with no implicit fallback."""

    def __init__(self) -> None:
        self._factories: dict[str, object] = {}

    def register(self, name: str, factory: object) -> None:
        key = name.strip().lower()
        if not key:
            raise ValueError("provider name cannot be empty")
        if key in self._factories:
            raise ValueError(f"provider already registered: {key}")
        self._factories[key] = factory

    def get_factory(self, name: str) -> object:
        try:
            return self._factories[name.strip().lower()]
        except KeyError as exc:
            raise ProviderError(f"provider is not configured: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))
