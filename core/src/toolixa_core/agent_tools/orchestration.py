"""Deterministic validation of bounded task dependency graphs."""

from __future__ import annotations

from collections import deque
import math
from typing import Any

from toolixa_core.tools.base import ToolCallContext, ToolSpec


def order_task_graph(tasks: list[dict[str, Any]], *, max_tasks: int = 100) -> list[str]:
    if not isinstance(tasks, list) or len(tasks) > max_tasks:
        raise ValueError(f"tasks must be a list with at most {max_tasks} entries")
    identifiers = []
    dependencies = {}
    for item in tasks:
        if not isinstance(item, dict):
            raise ValueError("each task must be an object")
        task_id, required = item.get("id"), item.get("depends_on", [])
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("every task requires a non-empty id")
        if task_id in dependencies:
            raise ValueError(f"duplicate task id: {task_id}")
        if not isinstance(required, list) or not all(isinstance(value, str) for value in required):
            raise ValueError(f"depends_on for {task_id} must be a list of strings")
        if task_id in required:
            raise ValueError(f"task cannot depend on itself: {task_id}")
        identifiers.append(task_id)
        dependencies[task_id] = required
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
    ordered = []
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


class ValidateTaskGraphTool:
    spec = ToolSpec(
        "orchestration.validate_task_graph",
        "Validate identifiers, dependencies, missing edges and cycles; return deterministic execution order without executing tasks or spawning agents.",
        (),
        {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "minLength": 1, "maxLength": 120},
                            "depends_on": {
                                "type": "array",
                                "maxItems": 100,
                                "items": {"type": "string", "minLength": 1, "maxLength": 120},
                            },
                        },
                        "required": ["id"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["tasks"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        del context
        tasks = arguments["tasks"]
        return {
            "task_count": len(tasks),
            "execution_order": order_task_graph(tasks),
            "validated": True,
            "tasks_executed": False,
            "agents_spawned": 0,
        }


class AnalyzeDeliveryPlanTool:
    spec = ToolSpec(
        "orchestration.analyze_delivery_plan",
        "Validate a bounded task dependency graph and compute an earliest/latest schedule, critical path, task slack, project duration and owner workload. This is planning analysis only; it does not execute tasks or spawn agents.",
        (),
        {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "minLength": 1, "maxLength": 120},
                            "title": {"type": "string", "maxLength": 240},
                            "depends_on": {
                                "type": "array",
                                "maxItems": 100,
                                "items": {"type": "string", "minLength": 1, "maxLength": 120},
                            },
                            "duration_hours": {"type": "number", "exclusiveMinimum": 0, "maximum": 10000},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                            "owner": {"type": "string", "maxLength": 120},
                        },
                        "required": ["id", "duration_hours"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["tasks"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        del context
        tasks = arguments["tasks"]
        order = order_task_graph(tasks)
        by_id = {item["id"]: item for item in tasks}
        duration: dict[str, float] = {}
        for task_id, item in by_id.items():
            value = item["duration_hours"]
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"duration_hours for {task_id} must be a finite positive number")
            duration[task_id] = float(value)

        predecessors: dict[str, str | None] = {}
        earliest_start: dict[str, float] = {}
        earliest_finish: dict[str, float] = {}
        children: dict[str, list[str]] = {task_id: [] for task_id in by_id}
        for task_id, item in by_id.items():
            for dependency in set(item.get("depends_on", [])):
                children[dependency].append(task_id)
        for task_id in order:
            dependencies = list(dict.fromkeys(by_id[task_id].get("depends_on", [])))
            previous = max(
                dependencies,
                key=lambda dependency: earliest_finish[dependency],
                default=None,
            )
            predecessors[task_id] = previous
            earliest_start[task_id] = earliest_finish[previous] if previous else 0.0
            earliest_finish[task_id] = earliest_start[task_id] + duration[task_id]

        final_task = max(order, key=lambda task_id: earliest_finish[task_id])
        project_duration = earliest_finish[final_task]
        latest_start: dict[str, float] = {}
        latest_finish: dict[str, float] = {}
        for task_id in reversed(order):
            dependents = children[task_id]
            finish = (
                min(latest_start[item] for item in dependents)
                if dependents
                else project_duration
            )
            latest_finish[task_id] = finish
            latest_start[task_id] = finish - duration[task_id]

        critical_path: list[str] = []
        cursor: str | None = final_task
        while cursor is not None:
            critical_path.append(cursor)
            cursor = predecessors[cursor]
        critical_path.reverse()

        schedule: dict[str, dict[str, Any]] = {}
        owner_load: dict[str, float] = {}
        for task_id in order:
            slack = max(0.0, latest_start[task_id] - earliest_start[task_id])
            item = by_id[task_id]
            owner = item.get("owner", "").strip()
            if owner:
                owner_load[owner] = owner_load.get(owner, 0.0) + duration[task_id]
            schedule[task_id] = {
                "title": item.get("title", ""),
                "duration_hours": duration[task_id],
                "earliest_start_hours": earliest_start[task_id],
                "earliest_finish_hours": earliest_finish[task_id],
                "latest_start_hours": latest_start[task_id],
                "latest_finish_hours": latest_finish[task_id],
                "slack_hours": round(slack, 6),
                "on_critical_path": task_id in critical_path,
                "priority": item.get("priority", 3),
                "owner": owner,
            }
        return {
            "task_count": len(order),
            "execution_order": order,
            "schedule": schedule,
            "critical_path": critical_path,
            "critical_path_duration_hours": project_duration,
            "project_duration_hours": project_duration,
            "total_effort_hours": sum(duration.values()),
            "owner_load_hours": dict(sorted(owner_load.items())),
            "tasks_executed": False,
            "agents_spawned": 0,
        }
