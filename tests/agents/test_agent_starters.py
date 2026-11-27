from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_agent(folder: str):
    path = ROOT / "agents" / folder / "main.py"
    module_name = "toolixa_test_" + folder.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_dev_copilot_reports_python_syntax_errors(tmp_path: Path):
    (tmp_path / "ok.py").write_text("answer = 42\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    result = load_agent("01-dev-copilot").analyze_workspace(tmp_path)
    assert result["files_scanned"] == 2
    assert result["syntax_errors"][0]["file"] == "bad.py"


def test_aegis_reports_secret_without_leaking_value():
    secret = "sk_live_abcdefghijklmnop1234"
    findings = load_agent("02-aegis-security").scan_text(f'API_KEY = "{secret}"\n', "settings.py")
    assert findings
    assert findings[0]["rule"] == "POSSIBLE_HARDCODED_SECRET"
    assert secret not in json.dumps(findings)


def test_orchestrator_orders_dependencies_and_rejects_cycles():
    agent = load_agent("03-task-orchestrator")
    tasks = [
        {"id": "test", "depends_on": ["build"]},
        {"id": "build", "depends_on": ["design"]},
        {"id": "design", "depends_on": []},
    ]
    assert agent.order_tasks(tasks) == ["design", "build", "test"]
    with __import__("pytest").raises(ValueError, match="cycle"):
        agent.order_tasks([{"id": "a", "depends_on": ["b"]}, {"id": "b", "depends_on": ["a"]}])


def test_rag_retrieval_returns_source_ranges():
    agent = load_agent("04-rag-chatbot")
    chunks = agent.chunk_document("guide.md", "Payments are due monthly.\nLate fees may apply.\n")
    results = agent.retrieve(chunks, "monthly payments")
    assert results
    assert results[0]["source"] == "guide.md"
    assert results[0]["start_line"] == 1


def test_content_maestro_does_not_claim_research():
    brief = load_agent("05-content-maestro").build_brief("Credit scores")
    assert brief["research_status"] == "not_performed"
    assert brief["sources"] == []
    assert brief["fact_check"]


def test_web_scraper_parses_local_html_only():
    html = """
    <html><head><title>Example</title>
    <meta name="description" content="A sample page"></head>
    <body><h1>Hello</h1><a href="/guide">Guide</a>
    <a href="javascript:alert(1)">bad</a></body></html>
    """
    result = load_agent("06-web-scraper").extract_html(html, base_url="https://example.org/page")
    assert result["title"] == "Example"
    assert result["description"] == "A sample page"
    assert result["links"] == [{"text": "Guide", "href": "https://example.org/guide"}]
    assert result["network_requests"] == 0


def test_web_scraper_zero_link_limit_returns_no_links():
    result = load_agent("06-web-scraper").extract_html(
        '<a href="https://example.org">Example</a>', max_links=0
    )
    assert result["links"] == []
    assert result["links_returned"] == 0
