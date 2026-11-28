"""Model-driven test engineer with static source and syntax inspection."""

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import (
    InspectPythonTool,
    ListWorkspaceFilesTool,
    ReadWorkspaceFileTool,
    SearchWorkspaceTool,
)
from toolixa_core.runtime.agent import AgentDefinition


def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="test-engineer",
        name="Test Engineer",
        system_prompt=(
            "You are a senior test engineer. Map source modules to existing tests, inspect Python AST and syntax, "
            "identify behavioral gaps and propose focused pytest cases with fixtures and expected assertions. "
            "Prioritize high-risk behavior, edge cases, permissions and malformed inputs. "
            "Give exact test commands but DO NOT execute tests or commands, write files or claim tests passed. "
            "Use only evidence from the workspace tools and cite file paths/line numbers."
        ),
        min_tool_calls=1,
        tools=(
            ListWorkspaceFilesTool(),
            ReadWorkspaceFileTool(),
            SearchWorkspaceTool(),
            InspectPythonTool(),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "Test Engineer"))
