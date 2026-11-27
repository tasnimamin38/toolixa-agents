"""Read-only source inventory and Python syntax analysis."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

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


if __name__ == "__main__":
    main()
