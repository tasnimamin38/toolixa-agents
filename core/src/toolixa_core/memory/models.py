"""Provider-neutral memory records."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    document_id: str
    source: str
    text: str
    start_line: int
    end_line: int
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("invalid source line range")
