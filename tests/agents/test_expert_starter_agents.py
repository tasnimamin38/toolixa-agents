from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED = {
    "01-dev-copilot": {
        "id": "dev-copilot",
        "tools": {
            "workspace.list_files",
            "workspace.read_file",
            "workspace.search_text",
            "python.inspect_file",
            "git.read_diff",
        },
    },
    "02-aegis-security": {
        "id": "aegis-security",
        "tools": {"security.audit_source"},
    },
    "03-task-orchestrator": {
        "id": "task-orchestrator",
        "tools": {"orchestration.validate_task_graph"},
    },
    "04-rag-chatbot": {
        "id": "rag-chatbot",
        "tools": {
            "workspace.list_files",
            "workspace.read_file",
            "research.search_local_docs",
        },
    },
    "05-content-maestro": {
        "id": "content-maestro",
        "tools": {
            "workspace.list_files",
            "workspace.read_file",
            "research.search_local_docs",
            "content.validate_editorial_brief",
        },
    },
    "06-web-scraper": {
        "id": "web-scraper",
        "tools": {"html.extract_file"},
    },
}


def load_agent(folder: str):
    path = ROOT / "agents" / folder / "main.py"
    name = "toolixa_expert_starter_" + folder.replace("-", "_")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_all_six_original_agents_are_model_driven_expert_definitions():
    for folder, expected in EXPECTED.items():
        definition = load_agent(folder).build_agent()
        assert definition.id == expected["id"]
        assert {tool.spec.name for tool in definition.tools} == expected["tools"]
        assert definition.min_tool_calls >= 1
        assert definition.system_prompt.strip()
        assert len(definition.tools) >= 1


def test_each_original_agent_has_domain_specific_tools_not_only_generic_prompts():
    for folder, expected in EXPECTED.items():
        definition = load_agent(folder).build_agent()
        actual = {tool.spec.name for tool in definition.tools}
        assert actual == expected["tools"], folder


import json
from typing import Any

from toolixa_core.contracts.request import AgentRequest
from toolixa_core.contracts.response import AgentStatus
from toolixa_core.runtime.agent import ToolAgent


class StarterFakeClient:
    model = "test/expert-starter"

    def __init__(self, tool_name: str, arguments: dict[str, Any]):
        self.tool_name = tool_name
        self.arguments = arguments
        self.calls = 0
        self.evidence = ""

    def complete(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "starter-evidence-1",
                    "type": "function",
                    "function": {
                        "name": self.tool_name,
                        "arguments": json.dumps(self.arguments),
                    },
                }],
            }
            return {"choices": [{"index": 0, "message": message, "finish_reason": "tool_calls"}]}
        result = next(item for item in kwargs["messages"] if item.get("role") == "tool")
        self.evidence = result["content"]
        return {
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "Completed analysis from registered domain evidence."},
                "finish_reason": "stop",
            }]
        }


def prepare_agent_workspace(folder: str, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    if folder == "01-dev-copilot":
        (root / "module.py").write_text("def calculate(value):\\n    return value * 2\\n", encoding="utf-8")
    elif folder == "02-aegis-security":
        (root / "config.py").write_text('API_KEY = "sk_live_NEVER_RETURN_THIS_VALUE"\\n', encoding="utf-8")
    elif folder == "04-rag-chatbot":
        (root / "guide.md").write_text("# Refunds\\nRefunds are available within 30 days.\\n", encoding="utf-8")
    elif folder == "05-content-maestro":
        (root / "research.md").write_text("# Research\\nOfficial policy page is available from the regulator.\\n", encoding="utf-8")
    elif folder == "06-web-scraper":
        (root / "page.html").write_text(
            '<html><head><title>Sample</title><meta name="description" content="Fixture"></head>'
            '<body><h1>Sample heading</h1><a href="/guide">Guide</a></body></html>',
            encoding="utf-8",
        )


def test_all_six_original_agents_call_their_domain_tool_end_to_end(tmp_path: Path):
    scenarios = {
        "01-dev-copilot": ("workspace.list_files", {"max_files": 20}, True),
        "02-aegis-security": ("security.audit_source", {"max_files": 20}, True),
        "03-task-orchestrator": (
            "orchestration.validate_task_graph",
            {"tasks": [{"id": "design"}, {"id": "build", "depends_on": ["design"]}]},
            False,
        ),
        "04-rag-chatbot": ("research.search_local_docs", {"query": "refund", "max_results": 5}, True),
        "05-content-maestro": (
            "content.validate_editorial_brief",
            {
                "title": "Refund rights",
                "audience": "Consumers",
                "content_format": "video",
                "sections": ["Eligibility", "How to claim"],
                "claims": [{"claim": "Refunds may be available", "source_urls": ["https://example.org/policy"]}],
            },
            True,
        ),
        "06-web-scraper": ("html.extract_file", {"path": "page.html", "max_links": 10}, True),
    }
    for folder, (tool_name, arguments, needs_workspace) in scenarios.items():
        workspace = tmp_path / folder if needs_workspace else None
        if workspace is not None:
            prepare_agent_workspace(folder, workspace)
        definition = load_agent(folder).build_agent()
        client = StarterFakeClient(tool_name, arguments)
        grants = set()
        if needs_workspace:
            grants.add("workspace.read")
        if folder == "02-aegis-security":
            grants.add("security.scan.passive")
        result = ToolAgent(client, definition).run(
            AgentRequest(
                agent_id=definition.id,
                input={"prompt": "Perform a complex domain task and ground the report in evidence."},
                workspace=str(workspace) if workspace is not None else None,
                grants=frozenset(grants),
            )
        )
        assert result.status is AgentStatus.SUCCEEDED, (folder, result.diagnostics)
        assert result.usage["tool_calls"] == 1
        assert client.calls == 2
        assert client.evidence
        assert result.output["answer"] == "Completed analysis from registered domain evidence."
        if folder == "02-aegis-security":
            assert "NEVER_RETURN_THIS_VALUE" not in client.evidence
