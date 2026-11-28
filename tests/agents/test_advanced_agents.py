from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from toolixa_core.contracts.request import AgentRequest
from toolixa_core.contracts.response import AgentStatus
from toolixa_core.runtime.agent import ToolAgent

ROOT = Path(__file__).resolve().parents[2]
ADVANCED = {
    "07-software-engineer": {
        "id": "software-engineer",
        "tools": {
            "workspace.list_files",
            "workspace.read_file",
            "workspace.search_text",
            "python.inspect_file",
            "git.read_diff",
        },
        "path": "workspace.list_files",
        "arguments": {"max_files": 20},
        "fixture": "source",
    },
    "08-code-reviewer": {
        "id": "code-reviewer",
        "tools": {
            "git.read_diff",
            "workspace.read_file",
            "workspace.search_text",
            "python.inspect_file",
        },
        "path": "git.read_diff",
        "arguments": {"max_chars": 2000},
        "fixture": "git",
    },
    "09-test-engineer": {
        "id": "test-engineer",
        "tools": {
            "workspace.list_files",
            "workspace.read_file",
            "workspace.search_text",
            "python.inspect_file",
        },
        "path": "python.inspect_file",
        "arguments": {"path": "module.py"},
        "fixture": "source",
    },
    "10-data-analyst": {
        "id": "data-analyst",
        "tools": {"workspace.list_files", "workspace.read_file", "data.profile_csv"},
        "path": "data.profile_csv",
        "arguments": {"path": "metrics.csv"},
        "fixture": "csv",
    },
    "11-api-architect": {
        "id": "api-architect",
        "tools": {"workspace.list_files", "workspace.read_file", "api.inspect_openapi_json", "api.compare_openapi_contracts"},
        "path": "api.inspect_openapi_json",
        "arguments": {"path": "openapi.json"},
        "fixture": "openapi",
    },
    "12-research-analyst": {
        "id": "research-analyst",
        "tools": {"workspace.list_files", "workspace.read_file", "research.search_local_docs"},
        "path": "research.search_local_docs",
        "arguments": {"query": "encrypted credentials"},
        "fixture": "docs",
    },
}


def load_agent(folder: str):
    path = ROOT / "agents" / folder / "main.py"
    spec = importlib.util.spec_from_file_location(
        "toolixa_advanced_" + folder.replace("-", "_"), path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    model = "test/local-model"

    def __init__(self, tool_name: str, arguments: dict[str, Any]):
        self.tool_name = tool_name
        self.arguments = arguments
        self.calls = 0

    def complete(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "advanced-call-1",
                        "type": "function",
                        "function": {
                            "name": self.tool_name,
                            "arguments": json.dumps(self.arguments),
                        },
                    }
                ],
            }
            return {
                "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            }
        tool_message = next(item for item in kwargs["messages"] if item.get("role") == "tool")
        self.tool_content = tool_message["content"]
        return {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Analysis completed from tool evidence.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
        }


def prepare_fixture(kind: str, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if kind == "source":
        (root / "module.py").write_text(
            "def calculate(value):\n    if value:\n        return value * 2\n    return 0\n",
            encoding="utf-8",
        )
    elif kind == "csv":
        (root / "metrics.csv").write_text("month,revenue\nJan,10\nFeb,20\n", encoding="utf-8")
    elif kind == "openapi":
        data = {
            "openapi": "3.1.0",
            "info": {"title": "Sample API", "version": "1"},
            "paths": {
                "/items": {
                    "get": {"operationId": "listItems", "responses": {"200": {"description": "ok"}}}
                }
            },
        }
        (root / "openapi.json").write_text(json.dumps(data), encoding="utf-8")
    elif kind == "docs":
        (root / "guide.md").write_text(
            "# Security\nCredentials are encrypted at rest.\nKeys rotate yearly.\n",
            encoding="utf-8",
        )
    elif kind == "git":
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        source = root / "app.py"
        source.write_text("value = 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "app.py"], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.test",
                "commit",
                "-m",
                "baseline",
            ],
            check=True,
            capture_output=True,
        )
        source.write_text("value = 2\n", encoding="utf-8")


def test_all_six_advanced_agents_declare_real_distinct_tool_sets():
    for folder, expected in ADVANCED.items():
        agent = load_agent(folder).build_agent()
        assert agent.id == expected["id"]
        assert {tool.spec.name for tool in agent.tools} == expected["tools"]
        assert agent.system_prompt.strip()
        assert all("workspace.read" in tool.spec.required_permissions for tool in agent.tools)


def test_all_six_advanced_agents_execute_a_real_tool_call_end_to_end(tmp_path: Path):
    for folder, expected in ADVANCED.items():
        workspace = tmp_path / folder
        prepare_fixture(expected["fixture"], workspace)
        definition = load_agent(folder).build_agent()
        client = FakeClient(expected["path"], expected["arguments"])
        agent = ToolAgent(client, definition)
        result = agent.run(
            AgentRequest(
                agent_id=expected["id"],
                input={"prompt": "Inspect this project and report evidence."},
                workspace=str(workspace),
                grants=frozenset({"workspace.read"}),
            )
        )

        assert result.status is AgentStatus.SUCCEEDED, (folder, result.diagnostics)
        assert result.output["answer"] == "Analysis completed from tool evidence."
        assert result.usage["tool_calls"] == 1
        assert client.calls == 2
        assert client.tool_content


def test_each_advanced_agent_exposes_a_helpful_cli_without_provider_credentials():
    for folder in ADVANCED:
        path = ROOT / "agents" / folder / "main.py"
        environment = dict(__import__("os").environ)
        source_path = str(ROOT / "core" / "src")
        environment["PYTHONPATH"] = (
            source_path
            if not environment.get("PYTHONPATH")
            else source_path + __import__("os").pathsep + environment["PYTHONPATH"]
        )
        completed = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        assert completed.returncode == 0, (folder, completed.stderr)
        assert "--workspace" in completed.stdout
        assert "--grant" in completed.stdout
