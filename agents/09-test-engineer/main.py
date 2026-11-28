"""Expert test-engineering agent for static coverage and regression planning."""

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import (
    InspectPythonTool,
    ListWorkspaceFilesTool,
    MapPythonTestCoverageTool,
    ReadWorkspaceFileTool,
    SearchWorkspaceTool,
)
from toolixa_core.runtime.agent import AgentDefinition


def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="test-engineer",
        name="Test Engineer",
        system_prompt=(
            "You are a principal test architect. Map the repository's Python source and pytest structure first. "
            "Use the static source-to-test mapper to connect classes, functions and methods to test functions, "
            "identify symbols without visible test references, and state that this is static reference mapping, "
            "not runtime coverage. Inspect relevant source and existing tests, then design a risk-weighted test "
            "strategy with unit, integration, contract, regression, boundary, negative, concurrency and failure "
            "scenarios where appropriate. Specify fixtures, input partitions, expected invariants, test data "
            "protection and reproducible acceptance criteria. Do not execute tests, create files or claim that "
            "a test passed. Cite repository-relative paths and line numbers."
        ),
        tools=(
            ListWorkspaceFilesTool(),
            ReadWorkspaceFileTool(),
            SearchWorkspaceTool(),
            InspectPythonTool(),
            MapPythonTestCoverageTool(),
        ),
        min_tool_calls=1,
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__))
