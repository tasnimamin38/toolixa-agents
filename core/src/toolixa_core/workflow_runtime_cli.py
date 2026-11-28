"""CLI adapter for bounded multi-agent workflows."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence

from toolixa_core.contracts.request import AgentRequest, ExecutionBudget
from toolixa_core.providers.base import ProviderError
from toolixa_core.workflows.engineering import EngineeringWorkflow


def run_workflow_cli(
    workflow_factory: Callable[[], EngineeringWorkflow],
    *,
    description: str,
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("prompt", help="Engineering task to analyse, review and test-plan")
    parser.add_argument("--workspace", required=True, help="Local project directory to inspect")
    parser.add_argument(
        "--grant",
        action="append",
        choices=["workspace.read"],
        default=[],
        help="Explicitly grant the read-only workspace capability",
    )
    parser.add_argument("--max-steps", type=int, default=25)
    parser.add_argument("--max-tool-calls", type=int, default=20)
    parser.add_argument("--max-wall-seconds", type=float, default=120.0)
    args = parser.parse_args(argv)

    try:
        workflow = workflow_factory()
        request = AgentRequest(
            agent_id=EngineeringWorkflow.AGENT_ID,
            input={"prompt": args.prompt},
            workspace=args.workspace,
            grants=frozenset(args.grant),
            budget=ExecutionBudget(
                max_steps=args.max_steps,
                max_tool_calls=args.max_tool_calls,
                max_wall_seconds=args.max_wall_seconds,
            ),
        )
        result = workflow.run(request)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        if result.status.value == "succeeded":
            return 0
        if result.status.value == "needs_approval":
            return 3
        return 2
    except (ProviderError, ValueError) as exc:
        print(
            json.dumps(
                {"status": "failed", "error": str(exc)[:300]},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
