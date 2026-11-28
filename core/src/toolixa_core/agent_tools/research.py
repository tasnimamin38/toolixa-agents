"""Local document retrieval with precise source paths and line citations."""

from __future__ import annotations

import re
from typing import Any

from toolixa_core.agent_tools.workspace import is_excluded_path, workspace_root
from toolixa_core.logging import redact
from toolixa_core.tools.base import ToolCallContext, ToolSpec

_WORDS = re.compile(r"[a-zA-Z0-9_]{2,}")


class SearchLocalDocsTool:
    spec = ToolSpec(
        "research.search_local_docs",
        "Search local Markdown, reStructuredText and text documentation; return ranked excerpts with exact workspace-relative paths and line numbers. This tool does not search the internet.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2, "maxLength": 200},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        root = workspace_root(context)
        terms = list(
            dict.fromkeys(token.casefold() for token in _WORDS.findall(arguments["query"]))
        )
        if not terms:
            raise ValueError("query must contain at least one searchable term")
        maximum = arguments.get("max_results", 20)
        results: list[dict[str, Any]] = []
        files_scanned = 0
        truncated = False
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root)
            if is_excluded_path(relative) or path.suffix.lower() not in {
                ".md",
                ".rst",
                ".txt",
                ".adoc",
            }:
                continue
            if files_scanned >= 300:
                truncated = True
                break
            if path.stat().st_size > 262_144:
                continue
            files_scanned += 1
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(lines, start=1):
                lowered = line.casefold()
                score = sum(1 for term in terms if term in lowered)
                if score:
                    results.append(
                        {
                            "path": relative.as_posix(),
                            "line": line_number,
                            "score": score,
                            "excerpt": redact(line.strip())[:400],
                        }
                    )
        results.sort(key=lambda item: (-item["score"], item["path"], item["line"]))
        if len(results) > maximum:
            results = results[:maximum]
            truncated = True
        return {
            "query": arguments["query"],
            "results": results,
            "results_returned": len(results),
            "files_scanned": files_scanned,
            "truncated": truncated,
            "search_scope": "local_workspace_only",
        }
