from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from toolixa_core.contracts.response import AgentStatus
from toolixa_core.runtime.agent import AgentDefinition
from toolixa_core.tools.base import ToolSpec

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_github_agent.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("toolixa_github_runner_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    model = "test/github-runner-model"

    def __init__(self, tool_name: str, arguments: dict[str, Any]):
        self.tool_name = tool_name
        self.arguments = arguments
        self.calls = 0
        self.evidence = ""

    def complete(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "github-runner-tool-1",
                        "type": "function",
                        "function": {
                            "name": self.tool_name,
                            "arguments": json.dumps(self.arguments),
                        },
                    }
                ],
            }
            return {
                "choices": [
                    {"index": 0, "message": message, "finish_reason": "tool_calls"}
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }
        tool_message = next(item for item in kwargs["messages"] if item.get("role") == "tool")
        self.evidence = tool_message["content"]
        return {
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Completed from registered tool evidence.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        }


def test_remote_endpoint_requires_https_and_rejects_local_gateway():
    runner = load_runner()
    assert runner.validate_remote_endpoint("https://api.example.com/v1") == "https://api.example.com/v1"
    assert runner.validate_remote_endpoint("https://api.example.com/v1/") == "https://api.example.com/v1"
    for value in (
        "http://api.example.com/v1",
        "http://127.0.0.1:20128/v1",
        "https://localhost/v1",
        "https://10.0.0.8/v1",
        "https://user:password@api.example.com/v1",
        "https://api.example.com/v1?token=secret",
    ):
        with pytest.raises(ValueError):
            runner.validate_remote_endpoint(value)


def test_catalog_loader_exposes_only_registered_agents():
    runner = load_runner()
    entries = runner._read_catalog(ROOT)
    assert entries
    assert len(entries) == len({entry["id"] for entry in entries.values()})
    with pytest.raises(ValueError, match="not registered"):
        runner.build_registered_runtime("unregistered-agent", ROOT, FakeClient("noop", {}))


def test_all_catalog_agents_build_expert_definitions_with_domain_tools():
    runner = load_runner()
    entries = runner._read_catalog(ROOT)
    for agent_id in entries:
        runtime, grants = runner.build_registered_runtime(agent_id, ROOT, FakeClient("noop", {}))
        definitions = runner._collect_definitions(agent_id, runtime)
        assert definitions, agent_id
        assert all(definition.tools for definition in definitions), agent_id
        assert all(definition.min_tool_calls >= 1 for definition in definitions), agent_id
        assert grants.issubset(runner.ALLOWED_PERMISSIONS), agent_id


def test_runner_executes_registered_tool_and_derives_only_required_grants(tmp_path: Path):
    runner = load_runner()
    client = FakeClient(
        "orchestration.validate_task_graph",
        {
            "tasks": [
                {"id": "design"},
                {"id": "build", "depends_on": ["design"]},
                {"id": "verify", "depends_on": ["build"]},
            ]
        },
    )
    result = runner.run_registered_agent(
        "task-orchestrator",
        "Plan and validate a complex release workflow.",
        tmp_path,
        client=client,
    )
    assert result.status is AgentStatus.SUCCEEDED
    assert result.usage["tool_calls"] == 1
    assert client.calls == 2
    assert json.loads(client.evidence)["execution_order"] == ["design", "build", "verify"]
    assert result.output["answer"] == "Completed from registered tool evidence."


def test_runner_enforces_task_and_resource_budgets(tmp_path: Path):
    runner = load_runner()
    client = FakeClient("orchestration.validate_task_graph", {"tasks": [{"id": "a"}]})
    with pytest.raises(ValueError, match="characters"):
        runner.run_registered_agent(
            "task-orchestrator", "x" * 12_001, tmp_path, client=client
        )
    with pytest.raises(ValueError, match="max_steps"):
        runner.run_registered_agent(
            "task-orchestrator", "Plan safely.", tmp_path, client=client, max_steps=26
        )
    with pytest.raises(ValueError, match="max_wall_seconds"):
        runner.run_registered_agent(
            "task-orchestrator",
            "Plan safely.",
            tmp_path,
            client=client,
            max_wall_seconds=181,
        )
    assert client.calls == 0


def test_runner_refuses_unapproved_execution_permissions():
    runner = load_runner()

    class DangerousTool:
        spec = ToolSpec(
            "process.execute",
            "This tool must never be allowed by the GitHub runner.",
            ("process.execute",),
            {"type": "object", "properties": {}, "additionalProperties": False},
        )

    definition = AgentDefinition(
        id="unsafe",
        name="Unsafe",
        system_prompt="Do not run.",
        tools=(DangerousTool(),),
        min_tool_calls=1,
    )
    with pytest.raises(ValueError, match="does not grant"):
        runner._permissions((definition,))


def test_engineering_workflow_uses_fixed_registered_stages_and_read_only_grants():
    runner = load_runner()
    runtime, grants = runner.build_registered_runtime(
        "engineering-workflow", ROOT, FakeClient("noop", {})
    )
    assert [stage.id for stage in runtime.stages] == [
        "software-engineer",
        "code-reviewer",
        "test-engineer",
    ]
    assert grants == frozenset({"workspace.read"})
