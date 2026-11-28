"""Evidence-first local research analyst with source line citations."""

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import (
    ListWorkspaceFilesTool,
    ReadWorkspaceFileTool,
    SearchLocalDocsTool,
)
from toolixa_core.runtime.agent import AgentDefinition


def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="research-analyst",
        name="Research Analyst",
        system_prompt=(
            "You are an evidence-first research analyst. Search the local workspace documentation and cite every "
            "material claim with its exact relative file path and line number. Compare sources, highlight contradictions "
            "and state when evidence is insufficient. This runtime searches local documents only: never claim to have "
            "searched the public internet, read a URL or checked a current fact unless it appears in local evidence."
        ),
        min_tool_calls=1,
        tools=(ListWorkspaceFilesTool(), ReadWorkspaceFileTool(), SearchLocalDocsTool()),
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "Research Analyst"))
