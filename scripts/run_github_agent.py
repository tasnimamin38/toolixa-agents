"""Run one registered Toolixa agent on an ephemeral GitHub-hosted runner."""

from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from toolixa_core.contracts.request import AgentRequest, ExecutionBudget
from toolixa_core.contracts.response import AgentResult
from toolixa_core.logging import redact
from toolixa_core.providers.base import ProviderError
from toolixa_core.providers.chat import GatewayChatClient
from toolixa_core.runtime.agent import AgentDefinition, ToolAgent
from toolixa_core.workflows.engineering import EngineeringWorkflow

ALLOWED_PERMISSIONS = frozenset({"workspace.read", "security.scan.passive"})
MAX_TASK_CHARS = 12_000


def validate_remote_endpoint(value: str) -> str:
    """Require a remote HTTPS endpoint; never accept the local laptop Gateway."""
    candidate = value.strip()
    if not candidate or len(candidate) > 2048:
        raise ValueError("TOOLIXA_GATEWAY_URL must be a non-empty HTTPS endpoint URL")
    parsed = urlsplit(candidate)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("GitHub-hosted runs require an HTTPS endpoint without embedded credentials")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("loopback and private hostnames cannot be used by GitHub-hosted runners")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("endpoint IP must be globally routable")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("endpoint URL contains an invalid port") from exc
    return candidate.rstrip("/")


def _read_catalog(root: Path) -> dict[str, dict[str, Any]]:
    catalog_path = (root / "catalog" / "agents.json").resolve(strict=True)
    catalog_path.relative_to(root)
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("agents"), list):
        raise ValueError("the committed agent catalog is invalid")
    entries: dict[str, dict[str, Any]] = {}
    for entry in payload["agents"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise ValueError("the committed agent catalog contains an invalid entry")
        if entry["id"] in entries:
            raise ValueError("the committed agent catalog contains duplicate IDs")
        entries[entry["id"]] = entry
    return entries


def _load_registered_module(agent_id: str, root: Path) -> Any:
    entry = _read_catalog(root).get(agent_id)
    if entry is None:
        raise ValueError("agent_id is not registered in catalog/agents.json")
    directory = Path(entry.get("path", ""))
    entrypoint = Path(entry.get("entrypoint", ""))
    if (
        directory.is_absolute()
        or entrypoint.is_absolute()
        or ".." in directory.parts
        or ".." in entrypoint.parts
    ):
        raise ValueError("registered agent path is invalid")
    manifest_path = (root / directory / "agent.json").resolve(strict=True)
    module_path = (root / directory / entrypoint).resolve(strict=True)
    manifest_path.relative_to(root)
    module_path.relative_to(root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("id") != agent_id
        or manifest.get("entrypoint") != entrypoint.as_posix()
    ):
        raise ValueError("agent manifest and catalog identity do not match")
    if not module_path.is_file():
        raise ValueError("registered agent entrypoint is missing")
    module_name = "toolixa_github_agent_" + agent_id.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ValueError("registered agent entrypoint could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _collect_definitions(agent_id: str, runtime: Any) -> tuple[AgentDefinition, ...]:
    if agent_id == EngineeringWorkflow.AGENT_ID:
        if not isinstance(runtime, EngineeringWorkflow):
            raise TypeError("engineering workflow factory returned an invalid runtime")
        return tuple(stage.definition for stage in runtime.stages)
    if not isinstance(runtime, AgentDefinition):
        raise TypeError("agent factory must return an AgentDefinition")
    return (runtime,)


def _permissions(definitions: tuple[AgentDefinition, ...]) -> frozenset[str]:
    required = {
        permission
        for definition in definitions
        for tool in definition.tools
        for permission in tool.spec.required_permissions
    }
    unsupported = required - ALLOWED_PERMISSIONS
    if unsupported:
        raise ValueError(
            "GitHub runner does not grant these capabilities: "
            + ", ".join(sorted(unsupported))
        )
    return frozenset(required)


def build_registered_runtime(
    agent_id: str, root: Path, client: Any
) -> tuple[Any, frozenset[str]]:
    """Load a catalogued agent and derive grants from its registered tools."""
    module = _load_registered_module(agent_id, root)
    if agent_id == EngineeringWorkflow.AGENT_ID:
        factory = getattr(module, "build_workflow", None)
        if not callable(factory):
            raise ValueError("engineering workflow does not expose build_workflow")
        runtime = factory(client=client)
    else:
        factory = getattr(module, "build_agent", None)
        if not callable(factory):
            raise ValueError("registered agent does not expose build_agent")
        runtime = factory()
    grants = _permissions(_collect_definitions(agent_id, runtime))
    return runtime, grants


def run_registered_agent(
    agent_id: str,
    task: str,
    workspace: Path,
    *,
    client: Any,
    max_steps: int = 12,
    max_tool_calls: int = 12,
    max_wall_seconds: float = 120.0,
) -> AgentResult:
    """Execute a registered read-only agent with a bounded request budget."""
    if not isinstance(task, str) or not task.strip() or len(task) > MAX_TASK_CHARS:
        raise ValueError("task must contain between 1 and 12000 characters")
    if not 1 <= max_steps <= 25:
        raise ValueError("max_steps must be between 1 and 25")
    if not 1 <= max_tool_calls <= 25:
        raise ValueError("max_tool_calls must be between 1 and 25")
    if not 10 <= max_wall_seconds <= 180:
        raise ValueError("max_wall_seconds must be between 10 and 180")
    root = workspace.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("GitHub workspace must be an existing directory")
    runtime, grants = build_registered_runtime(agent_id, root, client)
    if agent_id == EngineeringWorkflow.AGENT_ID and (max_steps < 3 or max_tool_calls < 3):
        raise ValueError("engineering-workflow requires at least three steps and tool calls")
    request = AgentRequest(
        agent_id=agent_id,
        input={"prompt": task},
        workspace=str(root) if "workspace.read" in grants else None,
        grants=grants,
        budget=ExecutionBudget(
            max_steps=max_steps,
            max_tool_calls=max_tool_calls,
            max_wall_seconds=max_wall_seconds,
        ),
    )
    if agent_id == EngineeringWorkflow.AGENT_ID:
        return runtime.run(request)
    return ToolAgent(client, runtime).run(request)


def _safe_value(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        return redact(value[:20_000], known_secrets=secrets)
    if isinstance(value, list):
        return [_safe_value(item, secrets) for item in value[:100]]
    if isinstance(value, dict):
        return {
            str(key)[:100]: _safe_value(item, secrets)
            for key, item in list(value.items())[:100]
        }
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return str(type(value).__name__)


def _write_step_summary(
    payload: dict[str, Any], summary_path: str, secrets: tuple[str, ...]
) -> None:
    if not summary_path:
        return
    output = payload.get("output", {})
    answer = output.get("answer") or output.get("final_answer") or ""
    diagnostics = payload.get("diagnostics", [])
    lines = [
        "## Toolixa Agent Run",
        "",
        "Agent: " + str(payload.get("agent_id", "unknown")),
        "Status: " + str(payload.get("status", "unknown")),
        "Tool calls: " + str(payload.get("usage", {}).get("tool_calls", "n/a")),
        "",
        "### Result",
        "",
        redact(str(answer)[:16_000], known_secrets=secrets) or "No final answer returned.",
    ]
    if diagnostics:
        lines.extend(
            [
                "",
                "### Diagnostics",
                "",
                json.dumps(_safe_value(diagnostics, secrets), ensure_ascii=False, indent=2)[:8_000],
            ]
        )
    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_client() -> GatewayChatClient:
    endpoint = os.environ.get("TOOLIXA_GATEWAY_URL", "").strip()
    if not endpoint:
        raise ProviderError("repository variable TOOLIXA_GATEWAY_URL is required")
    validate_remote_endpoint(endpoint)
    if not os.environ.get("TOOLIXA_API_KEY", "").strip():
        raise ProviderError("repository secret TOOLIXA_API_KEY is required")
    if not os.environ.get("TOOLIXA_MODEL", "").strip():
        raise ProviderError("repository variable TOOLIXA_MODEL is required")
    return GatewayChatClient.from_env()


def main() -> int:
    secret = os.environ.get("TOOLIXA_API_KEY", "").strip()
    secrets = (secret,) if secret else ()
    try:
        agent_id = os.environ.get("TOOLIXA_RUN_AGENT_ID", "").strip()
        task = os.environ.get("TOOLIXA_RUN_TASK", "")
        workspace_value = os.environ.get("GITHUB_WORKSPACE", "").strip()
        if not agent_id:
            raise ValueError("workflow agent_id input is required")
        if not workspace_value:
            raise ValueError("GITHUB_WORKSPACE is required")
        client = _load_client()
        result = run_registered_agent(
            agent_id,
            task,
            Path(workspace_value),
            client=client,
            max_steps=int(os.environ.get("TOOLIXA_MAX_STEPS", "12")),
            max_tool_calls=int(os.environ.get("TOOLIXA_MAX_TOOL_CALLS", "12")),
            max_wall_seconds=float(os.environ.get("TOOLIXA_MAX_WALL_SECONDS", "120")),
        )
        payload = _safe_value(result.to_dict(), secrets)
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:40_000])
        _write_step_summary(payload, os.environ.get("GITHUB_STEP_SUMMARY", ""), secrets)
        if result.status.value == "succeeded":
            return 0
        if result.status.value == "needs_approval":
            return 3
        return 2
    except Exception as exc:
        message = redact(str(exc), known_secrets=secrets)[:300]
        failure = {"status": "failed", "error": message}
        print(json.dumps(failure, ensure_ascii=False), file=sys.stderr)
        _write_step_summary(
            {"agent_id": os.environ.get("TOOLIXA_RUN_AGENT_ID", "unknown"), **failure},
            os.environ.get("GITHUB_STEP_SUMMARY", ""),
            secrets,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
