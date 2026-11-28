"""Fixed, read-only Git diff inspection for a selected workspace."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from toolixa_core.agent_tools.workspace import workspace_root
from toolixa_core.logging import redact
from toolixa_core.tools.base import ToolCallContext, ToolSpec


class ReadGitDiffTool:
    spec = ToolSpec(
        "git.read_diff",
        "Read the current uncommitted Git diff without invoking a shell, pager, external diff driver or textconv. Output is capped.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {"max_chars": {"type": "integer", "minimum": 500, "maximum": 20000}},
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        root = workspace_root(context)
        maximum = arguments.get("max_chars", 12_000)
        if not 500 <= maximum <= 20_000:
            raise ValueError("max_chars must be between 500 and 20,000")
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "GIT_PAGER": "cat",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
        }
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-c",
                    "diff.external=",
                    "-c",
                    "core.pager=cat",
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--unified=3",
                ],
                cwd=root,
                env=environment,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                check=False,
            )
        except FileNotFoundError:
            return {"available": False, "reason": "git executable was not found", "diff": ""}
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "reason": "git diff exceeded the 5-second limit",
                "diff": "",
            }
        if completed.returncode != 0:
            return {
                "available": False,
                "reason": "workspace is not a readable Git repository",
                "diff": "",
            }
        diff = redact(completed.stdout)
        return {
            "available": True,
            "diff": diff[:maximum],
            "truncated": len(diff) > maximum,
            "characters_returned": min(len(diff), maximum),
        }
