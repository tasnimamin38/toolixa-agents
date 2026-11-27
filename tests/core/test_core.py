from pathlib import Path

import pytest

from toolixa_core.contracts.request import AgentRequest, ExecutionBudget
from toolixa_core.contracts.response import AgentResult, AgentStatus, ArtifactReference
from toolixa_core.providers.base import ProviderError, ProviderRegistry
from toolixa_core.runtime.executor import DisabledExecutor, ExecutionDisabled, ExecutionRequest
from toolixa_core.runtime.limits import BudgetExceeded, BudgetTracker
from toolixa_core.security.approvals import ApprovalManager
from toolixa_core.security.policy import RuntimePolicy
from toolixa_core.tools.base import ToolCallContext, ToolSpec
from toolixa_core.tools.registry import ToolRegistry


def test_request_and_result_are_json_compatible():
    request = AgentRequest(agent_id="sample-agent", input={"topic": "demo"})
    assert request.to_dict()["agent_id"] == "sample-agent"
    result = AgentResult("r1", "sample-agent", AgentStatus.SUCCEEDED, {"ok": True})
    assert result.to_dict()["status"] == "succeeded"


def test_budget_rejects_invalid_values():
    with pytest.raises(ValueError):
        ExecutionBudget(max_steps=0)


def test_artifact_path_cannot_escape_workspace():
    with pytest.raises(ValueError):
        ArtifactReference("../outside.txt")


def test_policy_denies_ungranted_and_outside_paths(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    policy = RuntimePolicy(
        granted_permissions=frozenset({"workspace.read"}),
        workspace_roots=(workspace,),
    )
    assert policy.decide("workspace.read", target=workspace / "notes.txt").allowed
    assert not policy.decide("workspace.write", target=workspace / "notes.txt").allowed
    assert not policy.decide("workspace.read", target=tmp_path / "outside.txt").allowed


def test_policy_requires_exact_allowed_host():
    policy = RuntimePolicy(
        granted_permissions=frozenset({"network.http"}),
        allowed_hosts=frozenset({"docs.example.org"}),
    )
    assert policy.decide("network.http", target="https://docs.example.org/page").allowed
    assert not policy.decide("network.http", target="http://127.0.0.1/").allowed
    assert not policy.decide("network.http", target="https://other.example.org/").allowed


def test_approval_is_action_target_bound_and_single_use():
    approvals = ApprovalManager()
    grant = approvals.issue(action="delete", target="workspace/report.txt")
    assert not approvals.consume(grant.token, action="delete", target="workspace/other.txt")
    assert approvals.consume(grant.token, action="delete", target="workspace/report.txt")
    assert not approvals.consume(grant.token, action="delete", target="workspace/report.txt")


def test_budget_tracker_enforces_step_limit():
    tracker = BudgetTracker(ExecutionBudget(max_steps=1, max_tool_calls=1))
    tracker.step()
    with pytest.raises(BudgetExceeded):
        tracker.step()


def test_provider_registry_has_no_implicit_fallback():
    registry = ProviderRegistry()
    registry.register("local", lambda: object())
    assert registry.names() == ("local",)
    with pytest.raises(ProviderError):
        registry.get_factory("missing")


def test_disabled_executor_never_launches_commands():
    executor = DisabledExecutor()
    with pytest.raises(ExecutionDisabled):
        executor.execute(ExecutionRequest(("python", "--version"), "."))


def test_tool_registry_checks_permissions_before_invoke():
    class ExampleTool:
        spec = ToolSpec("example", "test", ("workspace.write",))

        def invoke(self, arguments, context):
            return {"executed": True}

    policy = RuntimePolicy()
    context = ToolCallContext("r1", "t1", None, policy)
    registry = ToolRegistry()
    registry.register(ExampleTool())
    with pytest.raises(PermissionError):
        registry.invoke("example", {}, context)


def test_secret_redaction_masks_common_token_shapes():
    from toolixa_core.logging import redact

    value = "Authorization: Bearer abc.def api_key=secretvalue sk-abcdefghijklmnop"
    cleaned = redact(value)
    assert "abc.def" not in cleaned
    assert "secretvalue" not in cleaned
    assert "sk-abcdefghijklmnop" not in cleaned
