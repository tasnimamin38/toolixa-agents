"""Read-only source inventory and Python syntax analysis."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import (
    InspectPythonTool, ListWorkspaceFilesTool, ReadGitDiffTool,
    ReadWorkspaceFileTool, SearchWorkspaceTool,
)
from toolixa_core.runtime.agent import AgentDefinition

EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}


def analyze_workspace(workspace: str | Path, *, max_files: int = 500) -> dict[str, object]:
    root = Path(workspace).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace must be a directory")
    if max_files < 1:
        raise ValueError("max_files must be positive")

    scanned = 0
    errors: list[dict[str, object]] = []
    truncated = False

    for candidate in sorted(root.rglob("*.py")):
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in candidate.parts):
            continue
        if candidate.is_symlink():
            continue
        resolved = candidate.resolve(strict=True)
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        if not resolved.is_file():
            continue
        if scanned >= max_files:
            truncated = True
            break

        scanned += 1
        try:
            source = resolved.read_text(encoding="utf-8")
            ast.parse(source, filename=str(relative))
        except UnicodeDecodeError:
            errors.append({"file": relative.as_posix(), "kind": "encoding", "message": "not UTF-8"})
        except SyntaxError as exc:
            errors.append(
                {
                    "file": relative.as_posix(),
                    "kind": "syntax",
                    "message": exc.msg,
                    "line": exc.lineno,
                    "column": exc.offset,
                }
            )

    return {
        "workspace": str(root),
        "files_scanned": scanned,
        "syntax_errors": errors,
        "truncated": truncated,
        "mode": "read-only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Local directory to inspect")
    parser.add_argument("--max-files", type=int, default=500)
    args = parser.parse_args()
    print(json.dumps(analyze_workspace(args.workspace, max_files=args.max_files), indent=2))



def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="dev-copilot",
        name="Dev Copilot",
        system_prompt=(
            "You are a principal software engineer and architecture analyst. First map the repository, identify its "
            "language/framework boundaries, entry points, dependencies, data flows and test topology. Use tools to "
            "inspect relevant files and Python syntax/AST evidence. For complex requests, produce a dependency-aware "
            "plan, affected modules, interface contracts, migration risks, security considerations and precise "
            "verification steps. Separate observed facts from hypotheses and cite repository-relative paths and "
            "line numbers. Never modify files, execute source, run commands or claim tests passed."
        ),
        tools=(ListWorkspaceFilesTool(), ReadWorkspaceFileTool(), SearchWorkspaceTool(),
               InspectPythonTool(), ReadGitDiffTool()),
        min_tool_calls=1,
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "01-dev-copilot"))
