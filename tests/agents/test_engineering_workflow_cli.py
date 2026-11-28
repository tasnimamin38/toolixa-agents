from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from toolixa_core.contracts.response import AgentResult, AgentStatus
from toolixa_core.workflow_runtime_cli import run_workflow_cli

ROOT = Path(__file__).resolve().parents[2]


class FakeWorkflow:
    def __init__(self, status: AgentStatus):
        self.status = status
        self.request = None

    def run(self, request):
        self.request = request
        return AgentResult(
            request_id=request.request_id,
            agent_id="engineering-workflow",
            status=self.status,
            output={"workflow": "engineering-workflow", "stages": [], "final_answer": "done"},
            usage={"steps": 0, "tool_calls": 0},
        )


def load_entrypoint():
    path = ROOT / "agents" / "13-engineering-workflow" / "main.py"
    spec = importlib.util.spec_from_file_location("toolixa_engineering_workflow_cli", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workflow_cli_help_does_not_require_gateway_credentials():
    environment = dict(os.environ)
    environment.pop("TOOLIXA_API_KEY", None)
    environment.pop("TOOLIXA_MODEL", None)
    source_path = str(ROOT / "core" / "src")
    environment["PYTHONPATH"] = (
        source_path
        if not environment.get("PYTHONPATH")
        else source_path + os.pathsep + environment["PYTHONPATH"]
    )

    completed = subprocess.run(
        [sys.executable, str(ROOT / "agents" / "13-engineering-workflow" / "main.py"), "--help"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--workspace" in completed.stdout
    assert "--grant" in completed.stdout
    assert "--max-steps" in completed.stdout
    assert "--max-tool-calls" in completed.stdout
    assert "--max-wall-seconds" in completed.stdout


def test_workflow_builder_uses_existing_specialists_in_fixed_order():
    module = load_entrypoint()

    workflow = module.build_workflow(client=object())

    assert [stage.id for stage in workflow.stages] == [
        "software-engineer",
        "code-reviewer",
        "test-engineer",
    ]
    assert [tool.spec.name for tool in workflow.stages[0].definition.tools] == [
        "workspace.list_files",
        "workspace.read_file",
        "workspace.search_text",
        "python.inspect_file",
        "git.read_diff",
    ]
    assert "git.read_diff" in {tool.spec.name for tool in workflow.stages[1].definition.tools}
    assert "python.inspect_file" in {tool.spec.name for tool in workflow.stages[2].definition.tools}


def test_workflow_cli_emits_json_and_returns_success_exit_code(tmp_path: Path, capsys):
    fake = FakeWorkflow(AgentStatus.SUCCEEDED)
    code = run_workflow_cli(
        lambda: fake,
        description="Test workflow",
        argv=[
            "Review code",
            "--workspace",
            str(tmp_path),
            "--grant",
            "workspace.read",
            "--max-steps",
            "9",
            "--max-tool-calls",
            "7",
            "--max-wall-seconds",
            "45",
        ],
    )

    output = json.loads(capsys.readouterr().out)
    assert code == 0
    assert output["status"] == "succeeded"
    assert fake.request.agent_id == "engineering-workflow"
    assert fake.request.budget.max_steps == 9
    assert fake.request.budget.max_tool_calls == 7
    assert fake.request.budget.max_wall_seconds == 45
    assert fake.request.grants == frozenset({"workspace.read"})


def test_workflow_cli_returns_needs_approval_exit_code(tmp_path: Path):
    fake = FakeWorkflow(AgentStatus.NEEDS_APPROVAL)
    code = run_workflow_cli(
        lambda: fake,
        description="Test workflow",
        argv=["Review code", "--workspace", str(tmp_path)],
    )

    assert code == 3


def test_workflow_cli_returns_failure_exit_code(tmp_path: Path):
    fake = FakeWorkflow(AgentStatus.FAILED)
    code = run_workflow_cli(
        lambda: fake,
        description="Test workflow",
        argv=["Review code", "--workspace", str(tmp_path), "--grant", "workspace.read"],
    )

    assert code == 2


def test_workflow_cli_reports_missing_gateway_key_without_fallback(tmp_path: Path):
    environment = dict(os.environ)
    environment.pop("TOOLIXA_API_KEY", None)
    environment.pop("TOOLIXA_MODEL", None)
    source_path = str(ROOT / "core" / "src")
    environment["PYTHONPATH"] = (
        source_path
        if not environment.get("PYTHONPATH")
        else source_path + os.pathsep + environment["PYTHONPATH"]
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "agents" / "13-engineering-workflow" / "main.py"),
            "Review this project",
            "--workspace",
            str(tmp_path),
            "--grant",
            "workspace.read",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    assert completed.returncode == 2
    error = json.loads(completed.stderr)
    assert error["status"] == "failed"
    assert "TOOLIXA_API_KEY is required" in error["error"]
