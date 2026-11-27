# Toolixa Agents

**A modular, local-first ecosystem of developer-operated AI agents.**

Toolixa is a source-code directory for independent agents. Bring your own runtime (BYOR), bring your own provider credentials (BYOK), and keep execution under your control.

## Agent directory

| Agent | Purpose | Status |
|---|---|---|
| Dev Copilot | Read-only workspace analysis and codebase inventory | Experimental |
| Aegis Security | Local passive source and secret-pattern checks | Experimental |
| Task Orchestrator | Bounded task dependency planning | Experimental |
| RAG Chatbot | Local text retrieval with file and line citations | Experimental |
| Content Maestro | Evidence-aware content brief and editorial outline | Experimental |
| Web Scraper | Parse supplied local HTML into structured metadata | Experimental |

The website catalog is generated from each agent's agent.json manifest.

## Quick start

Requirements: Python 3.11 or newer.

~~~powershell
git clone https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ./core
python -m pip install -r agents/06-web-scraper/requirements.txt
python -m pip install "pytest>=8,<9" "ruff>=0.8,<1"
python scripts/build_catalog.py
python -m pytest -q
~~~

Run an agent from its directory. For example:

~~~powershell
cd agents/01-dev-copilot
python main.py --workspace C:\path\to\your\project
~~~

See the README in each agent directory for its exact inputs, outputs, dependencies, and limitations.

## Design principles

- BYOR and BYOK are separate: Toolixa does not provide a hosted execution runtime.
- Agent dependencies are isolated; installing one agent does not require all other agents.
- Shared interfaces live in the small toolixa-core package.
- Permissions are explicit, deny by default, and do not come from the agent manifest.
- Arbitrary shell execution and active security testing are disabled by default.
- The static directory website does not execute Python agents.

## Project status

This is an early foundation release. Agent capabilities are intentionally bounded and documented. A starter agent is not an autonomous production system. Provider adapters, hardened remote executors, browser automation, and vector database integrations are optional future work and must not be assumed to exist.

## Security

Do not run an agent with permissions you have not reviewed. Use test workspaces and synthetic data first. Never commit API keys, tokens, cookies, private keys, real environment files, or sensitive customer data.

Report security issues privately to the repository owner rather than publishing exploit details.

## License status

No license has been selected. Public visibility does not itself grant permission to reuse, modify, or redistribute this repository. Licensing is intentionally on hold at the owner's direction.

## Documentation

- Architecture: docs/architecture.md
- Security model: docs/security-model.md
- BYOR guide: docs/byor-guide.md
- Installation: docs/installation.md
- Development: docs/development.md
- Approved design specification: docs/specs/2026-11-27-toolixa-agents-design.md
- Implementation plan: docs/plans/2026-11-27-toolixa-agents-implementation.md
