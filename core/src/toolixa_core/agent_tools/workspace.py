"""Workspace-bounded read-only file inventory, read and search tools."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath
from typing import Any

from toolixa_core.logging import redact
from toolixa_core.tools.base import ToolCallContext, ToolSpec

_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
}
_ALLOWED_HIDDEN_DIRS = {".github", ".vscode"}
_SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials.json",
    "secrets.json",
    "vault.key",
    "id_rsa",
    "id_ed25519",
    "service-account.json",
}
_TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".md",
    ".txt",
    ".rst",
    ".toml",
    ".ini",
    ".cfg",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sql",
    ".sh",
    ".ps1",
    ".bat",
    ".csv",
    ".gitignore",
    ".dockerfile",
}


def workspace_root(context: ToolCallContext) -> Path:
    if context.workspace is None:
        raise PermissionError("a workspace directory is required")
    root = context.workspace.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace must be a directory")
    context.policy.require("workspace.read", target=root)
    return root


def is_sensitive_path(path: Path) -> bool:
    name = path.name.lower()
    return (
        name in _SENSITIVE_NAMES
        or name.endswith((".pem", ".key", ".p12", ".pfx", ".kdbx"))
        or "credentials" in name
        or "secret" in name
    )


def is_excluded_path(relative: Path) -> bool:
    for part in relative.parts:
        if part in _EXCLUDED_DIRS:
            return True
        if part.startswith(".") and part not in _ALLOWED_HIDDEN_DIRS:
            return True
    return is_sensitive_path(relative)


def resolve_workspace_file(context: ToolCallContext, value: str) -> tuple[Path, Path]:
    root = workspace_root(context)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path must be a non-empty workspace-relative path")
    relative = Path(value)
    windows_relative = PureWindowsPath(value)
    if (
        relative.is_absolute()
        or windows_relative.is_absolute()
        or windows_relative.drive
        or ".." in relative.parts
        or ".." in windows_relative.parts
    ):
        raise PermissionError("path must remain inside the selected workspace")
    if is_excluded_path(relative):
        raise PermissionError("hidden or credential-bearing paths are not available to agents")

    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise PermissionError("symlink paths are not available to agents")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError("path resolves outside the selected workspace") from exc
    if not resolved.is_file():
        raise ValueError("path must reference a regular file")
    return root, resolved


def read_workspace_text(
    context: ToolCallContext, value: str, *, max_bytes: int = 262_144
) -> tuple[Path, str]:
    root, path = resolve_workspace_file(context, value)
    if path.stat().st_size > max_bytes:
        raise ValueError(f"file exceeds the {max_bytes}-byte read limit")
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("file is not valid UTF-8 text") from exc
    return path.relative_to(root), content


class ListWorkspaceFilesTool:
    spec = ToolSpec(
        "workspace.list_files",
        "List bounded, non-hidden text/source files under the selected workspace. Secret files and symlinks are excluded.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {"max_files": {"type": "integer", "minimum": 1, "maximum": 500}},
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        root = workspace_root(context)
        max_files = arguments.get("max_files", 200)
        if (
            not isinstance(max_files, int)
            or isinstance(max_files, bool)
            or not 1 <= max_files <= 500
        ):
            raise ValueError("max_files must be between 1 and 500")
        files: list[dict[str, Any]] = []
        truncated = False
        for candidate in sorted(root.rglob("*")):
            try:
                relative = candidate.relative_to(root)
            except ValueError:
                continue
            if is_excluded_path(relative) or candidate.is_symlink() or not candidate.is_file():
                continue
            resolved = candidate.resolve(strict=True)
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            if resolved.stat().st_size > 524_288:
                continue
            if resolved.suffix.lower() not in _TEXT_SUFFIXES and resolved.name.lower() not in {
                "dockerfile",
                "makefile",
                ".gitignore",
            }:
                continue
            if len(files) >= max_files:
                truncated = True
                break
            files.append(
                {
                    "path": relative.as_posix(),
                    "bytes": resolved.stat().st_size,
                    "extension": resolved.suffix.lower() or resolved.name.lower(),
                }
            )
        return {"files": files, "files_returned": len(files), "truncated": truncated}


class ReadWorkspaceFileTool:
    spec = ToolSpec(
        "workspace.read_file",
        "Read a UTF-8 text file inside the selected workspace with line numbers. Credential files, hidden files and symlinks are blocked; common secrets are redacted.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 500},
                "start_line": {"type": "integer", "minimum": 1, "maximum": 100_000},
                "max_lines": {"type": "integer", "minimum": 1, "maximum": 400},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        relative, content = read_workspace_text(context, arguments["path"])
        lines = content.splitlines()
        start = arguments.get("start_line", 1)
        limit = arguments.get("max_lines", 200)
        selected = lines[start - 1 : start - 1 + limit]
        numbered = [
            f"{start + index:04d}: {redact(line)[:1000]}" for index, line in enumerate(selected)
        ]
        return {
            "path": relative.as_posix(),
            "start_line": start,
            "end_line": start + len(selected) - 1 if selected else start - 1,
            "total_lines": len(lines),
            "truncated": start - 1 + len(selected) < len(lines),
            "content": "\n".join(numbered)[:30_000],
        }


class SearchWorkspaceTool:
    spec = ToolSpec(
        "workspace.search_text",
        "Search exact text in bounded UTF-8 source/document files inside the selected workspace and return matching line evidence.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 2, "maxLength": 120},
                "max_matches": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        root = workspace_root(context)
        query = arguments["query"].casefold()
        maximum = arguments.get("max_matches", 30)
        matches: list[dict[str, Any]] = []
        files_scanned = 0
        truncated = False
        for candidate in sorted(root.rglob("*")):
            if candidate.is_symlink() or not candidate.is_file():
                continue
            relative = candidate.relative_to(root)
            if is_excluded_path(relative) or candidate.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            if files_scanned >= 300:
                truncated = True
                break
            if candidate.stat().st_size > 131_072:
                continue
            files_scanned += 1
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(lines, start=1):
                if query in line.casefold():
                    matches.append(
                        {
                            "path": relative.as_posix(),
                            "line": line_number,
                            "excerpt": redact(line.strip())[:300],
                        }
                    )
                    if len(matches) >= maximum:
                        truncated = True
                        break
            if len(matches) >= maximum:
                break
        return {
            "query": arguments["query"],
            "matches": matches,
            "matches_returned": len(matches),
            "files_scanned": files_scanned,
            "truncated": truncated,
        }
