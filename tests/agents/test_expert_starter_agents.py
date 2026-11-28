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
