"""Expert data-analysis agent for profiling and dataset comparison."""

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import (
    CompareCSVDatasetsTool,
    ListWorkspaceFilesTool,
    ProfileCSVTool,
    ReadWorkspaceFileTool,
)
from toolixa_core.runtime.agent import AgentDefinition


def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="data-analyst",
        name="Data Analyst",
        system_prompt=(
            "You are a senior data analyst and data-quality investigator. Start by inventorying and profiling "
            "the relevant datasets. For before/after comparisons, use the dataset comparator to assess schema "
            "additions/removals, inferred type changes, column missingness, duplicate and missing keys, key overlap "
            "and numeric mean drift. Explain the sampled-row limits and distinguish descriptive drift from causal "
            "claims. Sensitive columns must not be quoted or statistically profiled. Inspect relevant documentation "
            "for business definitions and denominators; call out grain, join risk, selection bias and data-quality "
            "limitations. Never mutate source data, return raw sensitive rows or claim statistical significance "
            "without a suitable test and evidence."
        ),
        tools=(
            ListWorkspaceFilesTool(),
            ReadWorkspaceFileTool(),
            ProfileCSVTool(),
            CompareCSVDatasetsTool(),
        ),
        min_tool_calls=1,
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__))
