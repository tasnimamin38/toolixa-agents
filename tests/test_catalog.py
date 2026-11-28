import json
from pathlib import Path

from scripts.build_catalog import build_catalog, catalog_text

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_contains_thirteen_unique_agents_and_valid_paths():
    catalog = build_catalog(ROOT)
    agents = catalog["agents"]
    assert len(agents) == 13
    assert len({agent["id"] for agent in agents}) == 13
    assert {
        "software-engineer",
        "code-reviewer",
        "test-engineer",
        "data-analyst",
        "api-architect",
        "research-analyst",
        "engineering-workflow",
    }.issubset({agent["id"] for agent in agents})
    for agent in agents:
        base = ROOT / agent["path"]
        assert (base / agent["entrypoint"]).is_file()
        assert (base / agent["documentation"]).is_file()


def test_committed_catalog_matches_manifest_generation():
    actual = json.loads((ROOT / "catalog/agents.json").read_text(encoding="utf-8"))
    assert actual == build_catalog(ROOT)
    assert catalog_text(ROOT).endswith("\n")
