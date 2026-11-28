"""Bounded model-driven tool-calling runtime for local Toolixa agents."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from toolixa_core.contracts.request import AgentRequest
from toolixa_core.contracts.response import AgentResult, AgentStatus
from toolixa_core.logging import redact
from toolixa_core.providers.base import ProviderError
from toolixa_core.runtime.limits import BudgetExceeded, BudgetTracker
from toolixa_core.runtime.tool_calls import ToolArgumentError
from toolixa_core.security.policy import PermissionDenied, RuntimePolicy
from toolixa_core.tools.base import Tool
from toolixa_core.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    id: str
    name: str
    system_prompt: str
    tools: tuple[Tool, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip() or not self.system_prompt.strip():
            raise ValueError("agent id, name and system prompt must be non-empty")
        names = [tool.spec.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("agent tool names must be unique")


class ToolAgent:
    """Run one model conversation with sequential, policy-checked tool calls."""

    def __init__(
        self,
        client: Any,
        definition: AgentDefinition,
        *,
        max_prompt_chars: int = 50_000,
        max_tool_output_chars: int = 16_000,
    ) -> None:
        if max_prompt_chars < 256:
            raise ValueError("max_prompt_chars must be at least 256")
        if max_tool_output_chars < 128:
            raise ValueError("max_tool_output_chars must be at least 128")
        self.client = client
        self.definition = definition
        self.max_prompt_chars = max_prompt_chars
        self.max_tool_output_chars = max_tool_output_chars
        self.registry = ToolRegistry()
        for tool in definition.tools:
            self.registry.register(tool)

    @staticmethod
    def _usage(response: dict[str, Any]) -> dict[str, int]:
        usage = response.get("usage", {})
        if not isinstance(usage, dict):
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        result: dict[str, int] = {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = usage.get(key, 0)
            result[key] = (
                value
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0
                else 0
            )
        return result

    def _tool_result(self, value: dict[str, Any]) -> str:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        safe = redact(encoded)
        if len(safe) <= self.max_tool_output_chars:
            return safe
        preview_size = max(0, self.max_tool_output_chars - 64)
        bounded = json.dumps(
            {"truncated": True, "preview": safe[:preview_size]},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return bounded[: self.max_tool_output_chars]

    @staticmethod
    def _diagnostic(kind: str, message: str) -> dict[str, str]:
        return {"kind": kind, "message": redact(message)[:300]}

    def run(self, request: AgentRequest) -> AgentResult:
        if request.agent_id != self.definition.id:
            return self._failure(
                request, "agent_mismatch", "request agent_id does not match agent definition"
            )
        prompt = request.input.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return self._failure(
                request, "invalid_input", "input.prompt must be a non-empty string"
            )
        if len(prompt) > self.max_prompt_chars:
            return self._failure(
                request, "input_too_large", "input.prompt exceeds the configured size limit"
            )

        workspace = (
            Path(request.workspace).expanduser().resolve(strict=False)
            if request.workspace
            else None
        )
        roots = (workspace,) if workspace is not None else ()
        policy = RuntimePolicy(
            granted_permissions=request.grants,
            workspace_roots=roots,
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.definition.system_prompt},
            {"role": "user", "content": prompt},
        ]
        from toolixa_core.tools.base import ToolCallContext

        context = ToolCallContext(
            request_id=request.request_id,
            trace_id=request.trace_id,
            workspace=workspace,
            policy=policy,
        )
        tracker = BudgetTracker(request.budget)
        diagnostics: list[dict[str, str]] = []
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        tool_names = self.registry.names()
        denied_tool = False
        completed_calls = 0

        while True:
            try:
                tracker.step()
                remaining_seconds = request.budget.max_wall_seconds - (
                    time.monotonic() - tracker.started_at
                )
                if remaining_seconds <= 0:
                    raise BudgetExceeded("maximum wall-time budget exceeded")
                response = self.client.complete(
                    model=getattr(self.client, "model", ""),
                    messages=messages,
                    tools=self.registry.openai_tools(),
                    timeout_seconds=remaining_seconds,
                )
                if not isinstance(response, dict):
                    raise ProviderError("chat provider response must be an object")
                usage = self._usage(response)
                for key in total_usage:
                    total_usage[key] += usage[key]
                choices = response.get("choices")
                if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                    raise ProviderError("chat provider response has no completion choice")
                assistant = choices[0].get("message")
                if not isinstance(assistant, dict):
                    raise ProviderError("chat provider response has no assistant message")

                raw_calls = assistant.get("tool_calls", [])
                if raw_calls is None:
                    raw_calls = []
                if not isinstance(raw_calls, list):
                    raise ProviderError("assistant tool_calls must be an array")
                if not raw_calls:
                    answer = assistant.get("content")
                    if not isinstance(answer, str):
                        raise ProviderError("assistant returned no final text answer")
                    status = AgentStatus.NEEDS_APPROVAL if denied_tool else AgentStatus.SUCCEEDED
                    return AgentResult(
                        request_id=request.request_id,
                        agent_id=request.agent_id,
                        status=status,
                        output={
                            "answer": answer,
                            "tools_available": list(tool_names),
                            "tool_calls_executed": completed_calls,
                        },
                        usage={
                            **total_usage,
                            "model": getattr(self.client, "model", ""),
                            "tool_calls": completed_calls,
                            "steps": tracker.steps,
                        },
                        diagnostics=tuple(diagnostics),
                    )

                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant.get("content"),
                        "tool_calls": raw_calls,
                    }
                )
                seen_ids: set[str] = set()
                for call in raw_calls:
                    tracker.tool_call()
                    if not isinstance(call, dict):
                        raise ToolArgumentError("tool call entry must be an object")
                    call_id = call.get("id")
                    function = call.get("function")
                    if not isinstance(call_id, str) or not call_id or call_id in seen_ids:
                        raise ToolArgumentError("tool call ID must be unique and non-empty")
                    seen_ids.add(call_id)
                    if not isinstance(function, dict):
                        raise ToolArgumentError("tool call function must be an object")
                    name = function.get("name")
                    raw_arguments = function.get("arguments")
                    if not isinstance(name, str) or not isinstance(raw_arguments, str):
                        raise ToolArgumentError("tool call name and arguments must be strings")
                    if len(raw_arguments) > 24_000:
                        raise ToolArgumentError("tool arguments exceed the configured size limit")
                    try:
                        arguments = json.loads(raw_arguments)
                    except json.JSONDecodeError as exc:
                        raise ToolArgumentError("tool arguments are not valid JSON") from exc

                    try:
                        result = self.registry.invoke(name, arguments, context)
                    except PermissionDenied as exc:
                        denied_tool = True
                        diagnostics.append(self._diagnostic("permission_denied", str(exc)))
                        result = {"error": {"type": "permission_denied", "message": str(exc)}}
                    except KeyError as exc:
                        diagnostics.append(self._diagnostic("unknown_tool", str(exc)))
                        return self._failure(
                            request,
                            "unknown_tool",
                            "model requested a tool not registered for this agent",
                            diagnostics=diagnostics,
                            usage=total_usage,
                            steps=tracker.steps,
                            tool_calls=completed_calls,
                        )
                    except ToolArgumentError as exc:
                        diagnostics.append(self._diagnostic("invalid_tool_arguments", str(exc)))
                        return self._failure(
                            request,
                            "invalid_tool_arguments",
                            str(exc),
                            diagnostics=diagnostics,
                            usage=total_usage,
                            steps=tracker.steps,
                            tool_calls=completed_calls,
                        )
                    except Exception as exc:
                        diagnostics.append(self._diagnostic("tool_error", type(exc).__name__))
                        return self._failure(
                            request,
                            "tool_error",
                            "tool execution failed",
                            diagnostics=diagnostics,
                            usage=total_usage,
                            steps=tracker.steps,
                            tool_calls=completed_calls,
                        )

                    if not isinstance(result, dict):
                        return self._failure(
                            request,
                            "invalid_tool_result",
                            "tools must return a JSON object",
                            diagnostics=diagnostics,
                            usage=total_usage,
                            steps=tracker.steps,
                            tool_calls=completed_calls,
                        )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": self._tool_result(result),
                        }
                    )
                    if name in tool_names and "error" not in result:
                        completed_calls += 1
            except BudgetExceeded as exc:
                diagnostics.append(self._diagnostic("budget_exceeded", str(exc)))
                return self._failure(
                    request,
                    "budget_exceeded",
                    str(exc),
                    diagnostics=diagnostics,
                    usage=total_usage,
                    steps=tracker.steps,
                    tool_calls=completed_calls,
                )
            except ToolArgumentError as exc:
                diagnostics.append(self._diagnostic("invalid_tool_arguments", str(exc)))
                return self._failure(
                    request,
                    "invalid_tool_arguments",
                    str(exc),
                    diagnostics=diagnostics,
                    usage=total_usage,
                    steps=tracker.steps,
                    tool_calls=completed_calls,
                )
            except ProviderError as exc:
                diagnostics.append(self._diagnostic("provider_error", str(exc)))
                return self._failure(
                    request,
                    "provider_error",
                    str(exc),
                    diagnostics=diagnostics,
                    usage=total_usage,
                    steps=tracker.steps,
                    tool_calls=completed_calls,
                )

    def _failure(
        self,
        request: AgentRequest,
        kind: str,
        message: str,
        *,
        diagnostics: list[dict[str, str]] | None = None,
        usage: dict[str, int] | None = None,
        steps: int = 0,
        tool_calls: int = 0,
    ) -> AgentResult:
        items = list(diagnostics or [])
        items.append(self._diagnostic(kind, message))
        return AgentResult(
            request_id=request.request_id,
            agent_id=request.agent_id,
            status=AgentStatus.FAILED,
            output={"answer": ""},
            usage={
                **(usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
                "model": getattr(self.client, "model", ""),
                "tool_calls": tool_calls,
                "steps": steps,
            },
            diagnostics=tuple(items[:20]),
        )
