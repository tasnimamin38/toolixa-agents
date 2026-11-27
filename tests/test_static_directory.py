from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_static_site_uses_external_assets_and_catalog():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'src="/assets/app.js" defer' in html
    assert 'href="/assets/styles.css"' in html
    assert 'id="agent-grid"' in html
    assert (ROOT / "catalog/agents.json").is_file()


def test_frontend_uses_safe_dom_apis_not_html_injection():
    script = (ROOT / "assets/app.js").read_text(encoding="utf-8")
    assert "createElement" in script
    assert "textContent" in script
    assert "innerHTML" not in script


def test_vercel_config_is_static_and_has_security_headers():
    config = (ROOT / "vercel.json").read_text(encoding="utf-8")
    assert '"Content-Security-Policy"' in config
    assert '"X-Content-Type-Options"' in config
    assert '"functions"' not in config
