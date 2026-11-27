# Development Guide

## Repository layout

- core/ contains provider-neutral contracts and safety primitives.
- agents/ contains independent agent starters and manifests.
- catalog/ contains generated website data.
- scripts/ contains repository maintenance scripts.
- tests/ contains core, agent, catalog, and static-site checks.
- docs/ contains architecture and operational guidance.

## Environment setup

~~~powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ./core
python -m pip install "pytest>=8,<9" "ruff>=0.8,<1"
python -m pip install -r agents/06-web-scraper/requirements.txt
~~~

## Add an agent

1. Create a uniquely named folder under agents/.
2. Add main.py, agent.json, README.md, requirements.txt, and .env.example.
3. Use only canonical permission identifiers from core. A manifest declaration does not grant access.
4. Keep optional/heavy dependencies inside that agent.
5. Add focused tests under tests/agents.
6. Regenerate catalog/agents.json with python scripts/build_catalog.py.
7. Run all checks before committing.

The catalog builder validates relative entry-point/documentation paths and known permission names. It does not import or run agent code.

## Local quality checks

~~~powershell
python -m compileall -q core/src agents scripts tests
ruff check core/src agents scripts tests
ruff format --check core/src agents scripts tests
python scripts/build_catalog.py --check
python -m pytest -q
~~~

## Pull requests and CI

GitHub Actions runs compile, lint, formatting, catalog consistency, tests, and a dependency audit. CI does not require provider API keys or perform active network scans.

## Security review checklist

- Does the new agent request only the permissions it needs?
- Are paths constrained to selected workspaces?
- Does network access have exact host policy and an enforced egress boundary?
- Are redirects and DNS resolution handled safely?
- Are secrets omitted from logs, errors, manifests, and artifacts?
- Are tool results and retrieved data treated as untrusted?
- Is shell/process execution absent unless an approved isolated executor exists?
- Are tests deterministic and free of uncontrolled external requests?

## Current limitations

The initial executor always denies process execution. The Web Scraper parses local HTML only. Content Maestro does not browse. RAG uses lexical retrieval. Aegis performs passive local pattern checks. Task Orchestrator orders dependencies but does not launch agents. These limits are deliberate and must be updated in documentation when implementations materially change.
