"""Tool registry that validates schemas and enforces request policy."""

from __future__ import annotations

from typing import Any

from toolixa_core.runtime.tool_calls import validate_tool_arguments
from toolixa_core.security.policy import PermissionDenied
from toolixa_core.tools.base import Tool, ToolCallContext


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.spec.name.strip()
        if not name:
            raise ValueError("tool name cannot be empty")
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.spec.name,
                    "description": tool.spec.description,
                    "parameters": tool.spec.parameters,
                },
            }
            for tool in (self._tools[name] for name in self.names())
        ]

    def invoke(
        self, name: str, arguments: dict[str, Any], context: ToolCallContext
    ) -> dict[str, Any]:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        tool = self._tools[name]
        validate_tool_arguments(tool.spec.parameters, arguments)
        for permission in tool.spec.required_permissions:
            target = (
                context.workspace if permission in {"workspace.read", "workspace.write"} else None
            )
            decision = context.policy.decide(permission, target=target)
            if not decision.allowed:
                raise PermissionDenied(decision.reason)
        return tool.invoke(arguments, context)
