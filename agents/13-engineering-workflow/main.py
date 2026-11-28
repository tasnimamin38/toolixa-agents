"""Software Engineer -> Code Reviewer -> Test Engineer workflow."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from toolixa_core.providers.chat import GatewayChatClient
from toolixa_core.runtime.agent import AgentDefinition
from toolixa_core.workflow_runtime_cli import run_workflow_cli
from toolixa_core.workflows.engineering import EngineeringWorkflow, WorkflowStage

AGENT_ROOT = Path(__file__).resolve().parents[1]


def _load_definition(folder: str) -> AgentDefinition:
    module_path = AGENT_ROOT / folder / "main.py"
    module_name = f"toolixa_workflow_stage_{folder.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load specialist agent from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    definition = module.build_agent()
    if not isinstance(definition, AgentDefinition):
        raise TypeError(f"{folder} did not return an AgentDefinition")
    return definition


def build_workflow(client: Any | None = None) -> EngineeringWorkflow:
    """Build the fixed three-agent workflow; client injection supports tests."""
    gateway_client = client if client is not None else GatewayChatClient.from_env()
    stages = (
        WorkflowStage(
            "software-engineer", "Software Engineer", _load_definition("07-software-engineer")
        ),
        WorkflowStage("code-reviewer", "Code Reviewer", _load_definition("08-code-reviewer")),
        WorkflowStage("test-engineer", "Test Engineer", _load_definition("09-test-engineer")),
    )
    return EngineeringWorkflow(gateway_client, stages)


if __name__ == "__main__":
    raise SystemExit(
        run_workflow_cli(
            build_workflow,
            description=__doc__ or "Engineering Workflow Orchestrator",
        )
    )
