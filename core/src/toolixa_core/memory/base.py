"""Storage adapter protocol; no database is required by core."""

from typing import Protocol

from toolixa_core.memory.models import DocumentChunk


class MemoryStore(Protocol):
    def add(self, chunks: list[DocumentChunk]) -> None: ...

    def search(self, query: str, *, limit: int = 5) -> list[DocumentChunk]: ...