"""Model-driven API architect backed by local OpenAPI JSON inspection."""

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import (
    InspectOpenAPITool,
    ListWorkspaceFilesTool,
    ReadWorkspaceFileTool,
)
from toolixa_core.runtime.agent import AgentDefinition


def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="api-architect",
        name="API Architect",
        system_prompt=(
            "You are a principal API architect. Inspect local OpenAPI 3.x JSON contracts and related source files. "
            "Produce endpoint inventories, auth requirements that are actually documented, request/response models, "
            "integration gaps, compatibility risks and a concrete implementation map. Explicitly flag absent details. "
            "Do not call endpoints, fetch remote URLs, modify files or claim an integration has been deployed."
        ),
        min_tool_calls=1,
        tools=(ListWorkspaceFilesTool(), ReadWorkspaceFileTool(), InspectOpenAPITool()),
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "API Architect"))
