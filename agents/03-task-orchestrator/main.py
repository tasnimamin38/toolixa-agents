"""Deterministic task graph validation and topological ordering."""

from __future__ import annotations

import argparse
import json
from collections import deque
from typing import Any


from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import ValidateTaskGraphTool
from toolixa_core.runtime.agent import AgentDefinition

def order_tasks(tasks: list[dict[str, Any]], *, max_tasks: int = 100) -> list[str]:
    if len(tasks) > max_tasks:
        raise ValueError(f"task count exceeds limit of {max_tasks}")

    identifiers: list[str] = []
    dependencies: dict[str, list[str]] = {}
    for task in tasks:
        task_id = task.get("id")
        depends_on = task.get("depends_on", [])
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("every task must have a non-empty string id")
        if task_id in dependencies:
            raise ValueError(f"duplicate task id: {task_id}")
        if not isinstance(depends_on, list) or not all(
            isinstance(item, str) for item in depends_on
        ):
            raise ValueError(f"depends_on for {task_id} must be a list of task ids")
        if task_id in depends_on:
            raise ValueError(f"task cannot depend on itself: {task_id}")
        identifiers.append(task_id)
        dependencies[task_id] = depends_on

    known = set(identifiers)
    for task_id, required in dependencies.items():
        missing = sorted(set(required) - known)
        if missing:
            raise ValueError(f"task {task_id} has missing dependencies: {', '.join(missing)}")

    dependents = {task_id: [] for task_id in identifiers}
    indegree = {task_id: len(set(required)) for task_id, required in dependencies.items()}
    for task_id, required in dependencies.items():
        for dependency in required:
            dependents[dependency].append(task_id)

    ready = deque(task_id for task_id in identifiers if indegree[task_id] == 0)
    ordered: list[str] = []
    while ready:
        current = ready.popleft()
        ordered.append(current)
        for dependent in dependents[current]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)

    if len(ordered) != len(identifiers):
        cyclic = sorted(task_id for task_id, degree in indegree.items() if degree > 0)
        raise ValueError(f"dependency cycle detected: {', '.join(cyclic)}")
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON file with a tasks array")
    args = parser.parse_args()
    payload = json.loads(open(args.input, encoding="utf-8").read())
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        raise ValueError("input JSON must contain a tasks array")
    result = {"execution_order": order_tasks(payload["tasks"]), "mode": "plan-only"}
    print(json.dumps(result, indent=2))



def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="task-orchestrator",
        name="Task Orchestrator",
        system_prompt=(
            "You are a principal delivery architect. Decompose complex objectives into bounded, verifiable work "
            "packages with dependencies, acceptance criteria, owners/roles, risk gates and rollback points. Use the "
            "task-graph validator on the proposed dependency DAG, then revise any invalid graph. Identify critical "
            "path, parallelizable work and blocked prerequisites. You may plan delegation but must not launch agents, "
            "grant permissions, execute tasks or imply work has been performed."
        ),
        tools=(ValidateTaskGraphTool(),),
        min_tool_calls=1,
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "03-task-orchestrator"))
