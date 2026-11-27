# Toolixa Agents

**A modular, local-first ecosystem of developer-operated AI agents.**

**Live directory:** https://toolixa-agents.vercel.app

Toolixa is growing from an agent catalog into a local-first AI gateway and agent runtime. Bring your own runtime (BYOR), bring your own provider credentials (BYOK), and keep execution under your control.

## What exists today

| Component | Purpose | Status |
|---|---|---|
| Static Agent Directory | Browse six documented starter agents | Deployed |
| `toolixa-core` | Shared Python contracts, budgets, policies, tools, memory interfaces | Experimental foundation |
| Local AI Gateway | Browser dashboard, encrypted provider credentials, OpenAI-compatible local API | Experimental alpha |
| Six starter agents | Bounded local examples; see each README for exact behavior | Experimental |

### Starter agents

| Agent | Purpose |
|---|---|
| Dev Copilot | Read-only workspace analysis and codebase inventory |
| Aegis Security | Local passive source and secret-pattern checks |
| Task Orchestrator | Bounded task dependency planning |
| RAG Chatbot | Local text retrieval with file and line citations |
| Content Maestro | Evidence-aware content brief and editorial outline |
| Web Scraper | Parse supplied local HTML into structured metadata |

The directory catalog is generated from each agent's `agent.json` manifest.

## Local AI Gateway (experimental)

The gateway adds a local browser dashboard and a compatible API endpoint. It can connect to **any provider endpoint that implements the OpenAI Chat Completions-compatible API**, including cloud gateways, OpenRouter-compatible endpoints, Ollama's OpenAI-compatible endpoint, vLLM, LM Studio, and custom compatible servers.

It is not yet a universal adapter for every proprietary API protocol. Native Anthropic, Gemini, MCP client/tool execution, OAuth provider sign-in, and agent-runtime orchestration are planned as separate integrations.

### Install and run on Windows PowerShell

Requirements: Python 3.11+ and Git.

```powershell
git clone https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".\core[gateway]"
python -m toolixa_core.gateway
```

The command prints a one-time dashboard password and opens the browser. Open `http://127.0.0.1:20128` if it does not open automatically. The compatible API base is `http://127.0.0.1:20128/v1`.

1. Sign in with the first-run password shown in the terminal.
2. Add a provider name, its OpenAI-compatible API base URL, and its API key.
3. Use **Test connection** to discover models.
4. Try a model in the dashboard playground.
5. Create a Toolixa gateway API key and copy it immediately; the raw key is not shown again.
6. Connect a compatible client to the local `/v1` API. Use a model ID such as `provider-id/model-id`.

The dashboard only binds to `127.0.0.1`. Do not expose it through a public tunnel, reverse proxy, router port-forward, or a public server. Press `Ctrl+C` to stop it.

### Credential handling

Provider keys are encrypted in the local SQLite store using a Fernet key held separately from the repository under the current user's application-data directory. Toolixa API keys are displayed once and stored as hashes. This protects a database-only copy from revealing provider keys; it does not protect against malware or an attacker who can read both the local vault and its key. Never commit, paste into chat, or share real credentials.

### What this gateway does not do yet

- It does not call a paid provider during installation or tests.
- It does not run agent code, shell commands, browser automation, or MCP tools.
- It does not implement native adapters for every vendor API.
- It is single-user and local-only, not a remote multi-tenant SaaS service.
- It does not provide production-grade rate limits, audit controls, remote secret management, or high availability.

See [the gateway guide](docs/gateway-guide.md) for supported endpoint formats, API usage, storage paths, and limitations.

## Design principles

- BYOR and BYOK are separate: Toolixa does not provide a hosted execution runtime.
- The core SDK has no mandatory third-party runtime dependencies; the local gateway is an optional extra.
- Agent dependencies are isolated; installing one agent does not require all other agents.
- Permissions are explicit, deny by default, and do not come from the agent manifest.
- Arbitrary shell execution and active security testing are disabled by default.
- The agent logic, gateway, and server are Python. The dashboard is server-rendered HTML/CSS; no Node, Go, or Rust runtime is required.

## Development quick start

```powershell
python -m pip install -e "./core[gateway]"
python -m pip install -r agents/06-web-scraper/requirements.txt
python -m pip install "pytest>=8,<9" "ruff>=0.8,<1"
python scripts/build_catalog.py --check
python -m compileall -q core/src agents scripts tests
ruff check core/src agents scripts tests
ruff format --check core/src agents scripts tests
python -m pytest -q
```

## Project status and roadmap

This is an experimental local alpha, not a production-ready autonomous-agent platform.

1. **Local gateway foundation:** provider registry, local dashboard, encrypted BYOK storage, compatible model discovery, chat and stream proxy.
2. **Native AI and MCP integration:** native vendor adapters, MCP client/server registration and tool invocation, per-agent model selection, and real orchestration.
3. **Agent runtime:** permission-aware tool execution, workspace isolation, bounded process/container executor, browser tools, and source-aware vector memory.
4. **Production hardening:** threat-model review, CSRF/rate-limit hardening, observability, backup/recovery, signed audit events, supply-chain controls, and security testing.
5. **Optional hosted multi-user service:** tenant isolation, identity, KMS/secret manager, quotas, billing, operations and incident response.

A phase is complete only after automated tests, security review, and documented acceptance criteria pass. The static Vercel directory is not the Python gateway backend.

## Security

Do not run an agent with permissions you have not reviewed. Use test workspaces and synthetic data first. Never commit API keys, tokens, cookies, private keys, real environment files, or sensitive customer data.

Report security issues privately to the repository owner rather than publishing exploit details.

## License status

No license has been selected. Public visibility does not itself grant permission to reuse, modify, or redistribute this repository. Licensing is intentionally on hold at the owner's direction.

## Documentation

- Architecture: docs/architecture.md
- Security model: docs/security-model.md
- Gateway setup and API: docs/gateway-guide.md
- BYOR guide: docs/byor-guide.md
- Installation: docs/installation.md
- Development: docs/development.md
- Approved design specification: docs/specs/2026-11-27-toolixa-agents-design.md
- Implementation plan: docs/plans/2026-11-27-toolixa-agents-implementation.md
