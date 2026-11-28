"""Shared PowerShell-friendly CLI for model-powered specialist agents."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from toolixa_core.contracts.request import AgentRequest, ExecutionBudget
from toolixa_core.providers.base import ProviderError
from toolixa_core.providers.chat import GatewayChatClient
from toolixa_core.runtime.agent import AgentDefinition, ToolAgent


def run_agent_cli(
    definition: AgentDefinition,
    *,
    description: str,
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("prompt", help="Task or question for this specialist agent")
    parser.add_argument("--workspace", required=True, help="Local workspace to inspect")
    parser.add_argument(
        "--grant",
        action="append",
        choices=["workspace.read"],
        default=[],
        help="Explicitly grant a read-only capability (repeatable)",
    )
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--max-tool-calls", type=int, default=12)
    parser.add_argument("--max-wall-seconds", type=float, default=90.0)
    args = parser.parse_args(argv)

    try:
        client = GatewayChatClient.from_env()
        budget = ExecutionBudget(
            max_steps=args.max_steps,
            max_tool_calls=args.max_tool_calls,
            max_wall_seconds=args.max_wall_seconds,
        )
        request = AgentRequest(
            agent_id=definition.id,
            input={"prompt": args.prompt},
            workspace=args.workspace,
            grants=frozenset(args.grant),
            budget=budget,
        )
        result = ToolAgent(client, definition).run(request)
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
