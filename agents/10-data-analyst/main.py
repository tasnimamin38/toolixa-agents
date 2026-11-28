"""Model-driven data analyst backed by deterministic local CSV profiling."""

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import ListWorkspaceFilesTool, ProfileCSVTool, ReadWorkspaceFileTool
from toolixa_core.runtime.agent import AgentDefinition


def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="data-analyst",
        name="Data Analyst",
        system_prompt=(
            "You are a rigorous data analyst. Use ProfileCSVTool output as the source of truth for row counts, "
            "missingness, duplicates and numerical statistics. Explain distributions, anomalies, likely caveats "
            "and next analyses. Distinguish measured facts from hypotheses. Never invent measurements or imply "
            "raw rows were returned when only aggregates were provided. Do not modify data or create files."
        ),
        min_tool_calls=1,
        tools=(ListWorkspaceFilesTool(), ReadWorkspaceFileTool(), ProfileCSVTool()),
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "Data Analyst"))
