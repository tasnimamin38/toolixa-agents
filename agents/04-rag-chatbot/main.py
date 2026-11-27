"""Local text chunking and lexical retrieval with source line references."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from toolixa_core.memory.models import DocumentChunk

TOKEN = re.compile(r"[A-Za-z0-9_]{2,}")
EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}


def chunk_document(
    source: str, text: str, *, max_chars: int = 1200, overlap_lines: int = 2
) -> list[DocumentChunk]:
    if max_chars < 100 or overlap_lines < 0:
        raise ValueError("max_chars must be at least 100 and overlap_lines cannot be negative")
    lines = text.splitlines()
    if not lines:
        return []
    document_id = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    chunks: list[DocumentChunk] = []
    start = 0
    while start < len(lines):
        end = start
        size = 0
        while end < len(lines):
            next_size = len(lines[end]) + (1 if end > start else 0)
            if end > start and size + next_size > max_chars:
                break
            size += next_size
            end += 1
        selected = "\n".join(lines[start:end])
        chunks.append(
            DocumentChunk(
                document_id=document_id,
                source=source,
                text=selected,
                start_line=start + 1,
                end_line=end,
            )
        )
        if end >= len(lines):
            break
        start = max(start + 1, end - overlap_lines)
    return chunks


def index_workspace(workspace: str | Path, *, max_files: int = 1000, max_bytes: int = 1_000_000) -> list[DocumentChunk]:
    root = Path(workspace).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace must be a directory")
    if max_files < 1 or max_bytes < 1:
        raise ValueError("index limits must be positive")
    chunks: list[DocumentChunk] = []
    scanned = 0
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path.is_symlink():
            continue
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in path.parts):
            continue
        if path.suffix.lower() not in {".md", ".txt"} or path.stat().st_size > max_bytes:
            continue
        if scanned >= max_files:
            break
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        relative = path.resolve(strict=True).relative_to(root).as_posix()
        chunks.extend(chunk_document(relative, content))
    return chunks


def retrieve(chunks: list[DocumentChunk], query: str, *, limit: int = 5) -> list[dict[str, object]]:
    if limit < 1:
        raise ValueError("limit must be positive")
    terms = set(TOKEN.findall(query.casefold()))
    if not terms:
        return []
    ranked: list[tuple[int, DocumentChunk]] = []
    for chunk in chunks:
        words = TOKEN.findall(chunk.text.casefold())
        score = sum(words.count(term) for term in terms)
        if score:
            ranked.append((score, chunk))
    ranked.sort(key=lambda item: (-item[0], item[1].source, item[1].start_line))
    return [
        {
            "score": score,
            "source": chunk.source,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "text": chunk.text,
        }
        for score, chunk in ranked[:limit]
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--query", required=True)
    args = parser.parse_args()
    chunks = index_workspace(args.workspace)
    print(json.dumps({"results": retrieve(chunks, args.query), "chunks_indexed": len(chunks)}, indent=2))


if __name__ == "__main__":
    main()
