from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from toolixa_core.agent_tools.api import InspectOpenAPITool
from toolixa_core.agent_tools.data import ProfileCSVTool
from toolixa_core.agent_tools.git import ReadGitDiffTool
from toolixa_core.agent_tools.python import InspectPythonTool
from toolixa_core.agent_tools.research import SearchLocalDocsTool
from toolixa_core.agent_tools.workspace import (
    ListWorkspaceFilesTool,
    ReadWorkspaceFileTool,
    SearchWorkspaceTool,
)
from toolixa_core.security.policy import RuntimePolicy
from toolixa_core.tools.base import ToolCallContext


def context(root: Path) -> ToolCallContext:
    return ToolCallContext(
        request_id="test-request",
        trace_id="test-trace",
        workspace=root,
        policy=RuntimePolicy(
            granted_permissions=frozenset({"workspace.read"}),
            workspace_roots=(root,),
        ),
    )


def test_workspace_file_listing_excludes_secret_files_and_symlink_escape(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (root / ".env").write_text("API_KEY=sk-test-secret-value-1234567890\n", encoding="utf-8")
    secret_dir = root / ".git"
    secret_dir.mkdir()
    (secret_dir / "config").write_text("private", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    try:
        (root / "escape.txt").symlink_to(outside)
    except (OSError, NotImplementedError):
        pass

    result = ListWorkspaceFilesTool().invoke({"max_files": 20}, context(root))

    returned = [item["path"] for item in result["files"]]
    assert returned == ["main.py"]
    assert result["files_returned"] == 1
    assert ".env" not in json.dumps(result)
    assert "outside" not in json.dumps(result)


def test_workspace_reader_returns_requested_line_numbers_and_redacts_secrets(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    source = root / "settings.py"
    source.write_text(
        'title = "demo"\nAPI_KEY = "sk-test-secret-value-1234567890"\nmode = "safe"\n',
        encoding="utf-8",
    )

    result = ReadWorkspaceFileTool().invoke(
        {"path": "settings.py", "start_line": 2, "max_lines": 1},
        context(root),
    )

    assert result["start_line"] == 2
    assert result["end_line"] == 2
    assert "sk-test-secret-value-1234567890" not in result["content"]
    assert "[REDACTED]" in result["content"]


@pytest.mark.parametrize("path", ["../outside.txt", ".env", "C:\\Windows\\win.ini"])
def test_workspace_reader_rejects_escape_and_secret_paths(tmp_path: Path, path: str):
    root = tmp_path / "workspace"
    root.mkdir()
    with pytest.raises((ValueError, PermissionError)):
        ReadWorkspaceFileTool().invoke({"path": path}, context(root))


def test_workspace_search_returns_evidence_with_exact_line_numbers(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "guide.md").write_text(
        "# Overview\nPayments are processed daily.\nA separate note.\nPayments are reconciled weekly.\n",
        encoding="utf-8",
    )

    result = SearchWorkspaceTool().invoke(
        {"query": "Payments", "max_matches": 10},
        context(root),
    )

    assert [(hit["path"], hit["line"]) for hit in result["matches"]] == [
        ("guide.md", 2),
        ("guide.md", 4),
    ]


def test_python_inspector_reports_ast_symbols_and_syntax_without_execution(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "module.py").write_text(
        "import json\n\nclass Store:\n    def load(self, path):\n        if path:\n            return json.loads(path)\n        return None\n",
        encoding="utf-8",
    )

    result = InspectPythonTool().invoke({"path": "module.py"}, context(root))

    assert result["syntax_valid"] is True
    assert result["classes"][0]["name"] == "Store"
    assert result["functions"][0]["name"] == "load"
    assert result["imports"] == ["json"]
    assert result["complexity_nodes"] >= 1


def test_python_inspector_returns_syntax_error_location(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    result = InspectPythonTool().invoke({"path": "broken.py"}, context(root))

    assert result["syntax_valid"] is False
    assert result["syntax_error"]["line"] == 1


def test_csv_profiler_returns_hand_checkable_summary_statistics(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "sales.csv").write_text(
        "region,revenue,orders\nEast,10,1\nWest,20,2\nEast,30,3\n,40,4\n",
        encoding="utf-8",
    )

    result = ProfileCSVTool().invoke({"path": "sales.csv", "max_rows": 100}, context(root))

    assert result["rows_profiled"] == 4
    assert result["duplicate_rows"] == 0
    assert result["columns"]["revenue"]["minimum"] == 10.0
    assert result["columns"]["revenue"]["maximum"] == 40.0
    assert result["columns"]["revenue"]["mean"] == 25.0
    assert result["columns"]["region"]["missing"] == 1


def test_openapi_inspector_extracts_paths_operations_and_schemas(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Payments API", "version": "1.2.0"},
        "servers": [{"url": "https://api.example.test"}],
        "paths": {
            "/payments": {
                "get": {
                    "operationId": "listPayments",
                    "summary": "List payments",
                    "parameters": [{"name": "limit", "in": "query"}],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "createPayment",
                    "requestBody": {"required": True},
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
        "components": {"schemas": {"Payment": {"type": "object"}}},
    }
    (root / "openapi.json").write_text(json.dumps(spec), encoding="utf-8")

    result = InspectOpenAPITool().invoke({"path": "openapi.json"}, context(root))

    assert result["title"] == "Payments API"
    assert result["operation_count"] == 2
    assert result["operations"][0]["path"] == "/payments"
    assert "Payment" in result["schemas"]


def test_local_research_search_returns_document_path_and_line_evidence(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    docs = root / "docs"
    docs.mkdir()
    (docs / "security.md").write_text(
        "# Security\nCredentials are encrypted at rest.\nKeys rotate every quarter.\n",
        encoding="utf-8",
    )

    result = SearchLocalDocsTool().invoke(
        {"query": "encrypted credentials", "max_results": 10},
        context(root),
    )

    assert result["results"]
    assert result["results"][0]["path"] == "docs/security.md"
    assert result["results"][0]["line"] == 2
    assert "Credentials are encrypted at rest." in result["results"][0]["excerpt"]


def test_git_diff_tool_returns_read_only_diff_for_workspace(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "--allow-empty",
            "-m",
            "initial",
        ],
        check=True,
        capture_output=True,
    )
    source = root / "app.py"
    source.write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "app.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.test",
            "commit",
            "-m",
            "add app",
        ],
        check=True,
        capture_output=True,
    )
    source.write_text("value = 2\n", encoding="utf-8")

    result = ReadGitDiffTool().invoke({"max_chars": 2000}, context(root))

    assert result["available"] is True
    assert "value = 2" in result["diff"]
    assert "value = 1" in result["diff"]


def test_csv_profiler_never_returns_values_or_statistics_for_sensitive_columns(
    tmp_path: Path,
):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "private.csv").write_text(
        "password,api_token,card_number,revenue\n"
        "secret-phrase-1,token-value-1,4111111111111111,10\n"
        "secret-phrase-2,token-value-2,5555555555554444,20\n",
        encoding="utf-8",
    )

    result = ProfileCSVTool().invoke({"path": "private.csv", "max_rows": 100}, context(root))

    for name in ("password", "api_token", "card_number"):
        column = result["columns"][name]
        assert column["sensitive_column"] is True
        assert "unique_values" not in column
        assert "top_values" not in column
        assert "minimum" not in column
        assert "maximum" not in column
        assert "mean" not in column
        assert "median" not in column
    serialized = json.dumps(result)
    for secret in ("secret-phrase-1", "token-value-1", "4111111111111111"):
        assert secret not in serialized
