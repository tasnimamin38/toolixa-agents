from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolixa_core.agent_tools.api import CompareOpenAPIContractsTool
from toolixa_core.agent_tools.content import AnalyzeScriptTimelineTool
from toolixa_core.agent_tools.html import CrawlLocalHTMLSiteTool
from toolixa_core.agent_tools.orchestration import AnalyzeDeliveryPlanTool
from toolixa_core.agent_tools.python import AnalyzePythonModuleGraphTool
from toolixa_core.agent_tools.security import PythonSecurityASTTool
from toolixa_core.security.policy import RuntimePolicy
from toolixa_core.tools.base import ToolCallContext


def context(root: Path) -> ToolCallContext:
    return ToolCallContext(
        request_id="expert-domain-tool-test",
        trace_id="expert-domain-tool-test",
        workspace=root,
        policy=RuntimePolicy(
            granted_permissions=frozenset({"workspace.read", "security.scan.passive"}),
            workspace_roots=(root,),
        ),
    )


def test_security_ast_scanner_finds_unsafe_execution_and_deserialization_without_source_echo(
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    root.mkdir()
    source = root / "unsafe.py"
    source.write_text(
        "import pickle\n"
        "import subprocess\n"
        "def run(user_input):\n"
        "    payload = pickle.loads(user_input)\n"
        "    return subprocess.run(user_input, shell=True)\n"
        "eval(user_input)\n",
        encoding="utf-8",
    )

    result = PythonSecurityASTTool().invoke({"path": "unsafe.py"}, context(root))

    rules = {item["rule_id"] for item in result["findings"]}
    assert result["syntax_valid"] is True
    assert "PYTHON_UNSAFE_DESERIALIZATION" in rules
    assert "PYTHON_SUBPROCESS_SHELL_TRUE" in rules
    assert "PYTHON_DYNAMIC_EVAL" in rules
    assert all("source" not in item for item in result["findings"])
    assert result["source_code_returned"] is False


def test_security_ast_scanner_does_not_flag_literal_eval_or_shell_false(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "safe.py").write_text(
        "import ast\nimport subprocess\nvalue = ast.literal_eval(text)\n"
        "subprocess.run(['echo', 'safe'], shell=False)\n",
        encoding="utf-8",
    )

    result = PythonSecurityASTTool().invoke({"path": "safe.py"}, context(root))

    assert result["finding_count"] == 0


def test_delivery_plan_computes_critical_path_schedule_and_owner_load():
    result = AnalyzeDeliveryPlanTool().invoke(
        {
            "tasks": [
                {"id": "design", "duration_hours": 2, "owner": "architect"},
                {
                    "id": "backend",
                    "duration_hours": 3,
                    "owner": "backend",
                    "depends_on": ["design"],
                },
                {
                    "id": "frontend",
                    "duration_hours": 4,
                    "owner": "frontend",
                    "depends_on": ["design"],
                },
                {
                    "id": "integration",
                    "duration_hours": 1,
                    "owner": "backend",
                    "depends_on": ["backend", "frontend"],
                },
            ]
        },
        context(Path.cwd()),
    )

    assert result["project_duration_hours"] == 7
    assert result["critical_path"] == ["design", "frontend", "integration"]
    assert result["schedule"]["backend"]["slack_hours"] == 1
    assert result["owner_load_hours"] == {
        "architect": 2,
        "backend": 4,
        "frontend": 4,
    }
    assert result["tasks_executed"] is False


@pytest.mark.parametrize(
    "tasks",
    [
        [{"id": "a"}, {"id": "a"}],
        [{"id": "a", "depends_on": ["missing"]}],
        [{"id": "a", "depends_on": ["b"]}, {"id": "b", "depends_on": ["a"]}],
    ],
)
def test_delivery_plan_rejects_duplicate_missing_or_cyclic_dependencies(tasks):
    with pytest.raises(ValueError):
        AnalyzeDeliveryPlanTool().invoke({"tasks": tasks}, context(Path.cwd()))


def test_openapi_comparator_reports_backwards_incompatible_changes(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    before = {
        "openapi": "3.1.0",
        "info": {"title": "Payments", "version": "1.0.0"},
        "paths": {
            "/payments": {
                "post": {
                    "operationId": "createPayment",
                    "parameters": [{"name": "reference", "in": "query", "required": False, "schema": {"type": "string"}}],
                    "responses": {"201": {"description": "Created"}, "400": {"description": "Bad request"}},
                }
            }
        },
        "components": {
            "schemas": {
                "Payment": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "amount": {"type": "number"}},
                    "required": ["id"],
                }
            }
        },
    }
    after = {
        "openapi": "3.1.0",
        "info": {"title": "Payments", "version": "2.0.0"},
        "paths": {
            "/payments": {
                "post": {
                    "operationId": "createPayment",
                    "parameters": [{"name": "reference", "in": "query", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"400": {"description": "Bad request"}},
                }
            }
        },
        "components": {
            "schemas": {
                "Payment": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "currency": {"type": "string"}},
                    "required": ["id", "currency"],
                }
            }
        },
    }
    (root / "before.json").write_text(json.dumps(before), encoding="utf-8")
    (root / "after.json").write_text(json.dumps(after), encoding="utf-8")

    result = CompareOpenAPIContractsTool().invoke(
        {"before_path": "before.json", "after_path": "after.json"},
        context(root),
    )

    rules = {item["rule_id"] for item in result["changes"]}
    assert result["breaking_change_count"] >= 4
    assert "REQUIRED_PARAMETER_ADDED" in rules
    assert "PARAMETER_SCHEMA_CHANGED" in rules
    assert "RESPONSE_CODE_REMOVED" in rules
    assert "SCHEMA_PROPERTY_REMOVED" in rules
    assert "SCHEMA_REQUIRED_PROPERTY_ADDED" in rules


def test_content_timeline_detects_long_rehook_gaps_and_missing_final_cta():
    result = AnalyzeScriptTimelineTool().invoke(
        {
            "expected_duration_seconds": 120,
            "target_hook_interval_seconds": 40,
            "segments": [
                {"start_seconds": 0, "end_seconds": 15, "label": "Opening", "hook": True},
                {"start_seconds": 15, "end_seconds": 70, "label": "Setup", "hook": False},
                {"start_seconds": 70, "end_seconds": 105, "label": "Reveal", "hook": True},
                {"start_seconds": 105, "end_seconds": 120, "label": "Ending", "hook": False},
            ],
        },
        context(Path.cwd()),
    )

    assert result["timeline_valid"] is True
    assert any(item["gap_seconds"] > 40 for item in result["hook_gaps"])
    assert result["missing_final_cta"] is True
    assert result["retention_risk"] == "high"


def test_local_html_site_crawler_traverses_only_workspace_files(tmp_path: Path):
    root = tmp_path / "workspace"
    (root / "docs").mkdir(parents=True)
    (root / "index.html").write_text(
        '<html><head><title>Home</title></head><body>'
        '<h1>Welcome</h1><a href="/docs/guide.html">Guide</a>'
        '<a href="https://outside.example/path">External</a></body></html>',
        encoding="utf-8",
    )
    (root / "docs" / "guide.html").write_text(
        "<html><head><title>Guide</title></head><body><h1>Setup</h1></body></html>",
        encoding="utf-8",
    )

    result = CrawlLocalHTMLSiteTool().invoke(
        {"start_path": "index.html", "max_pages": 10, "max_depth": 3},
        context(root),
    )

    paths = {page["path"] for page in result["pages"]}
    assert paths == {"index.html", "docs/guide.html"}
    assert result["pages_crawled"] == 2
    assert result["network_requests"] == 0
    assert all("outside.example" not in json.dumps(page) for page in result["pages"])


def test_python_module_graph_detects_local_import_cycle_and_external_modules(tmp_path: Path):
    root = tmp_path / "workspace"
    (root / "package").mkdir(parents=True)
    (root / "package" / "__init__.py").write_text("", encoding="utf-8")
    (root / "package" / "alpha.py").write_text(
        "from package import beta\nimport json\n", encoding="utf-8"
    )
    (root / "package" / "beta.py").write_text(
        "from package import alpha\n", encoding="utf-8"
    )

    result = AnalyzePythonModuleGraphTool().invoke(
        {"max_files": 50},
        context(root),
    )

    assert result["module_count"] == 3
    assert result["cycle_count"] == 1
    assert {"package.alpha", "package.beta"}.issubset(set(result["cycles"][0]))
    assert "json" in result["external_imports"]
