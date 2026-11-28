<div align="center">
  <img src="assets/readme-hero.svg" alt="Toolixa Agents — a local-first ecosystem for modular AI agents" width="100%" />

  <p><strong>Build, connect and operate modular AI agents with your own models, tools and runtime.</strong></p>

  <p>
    <a href="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/ci.yml"><img src="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI status" /></a>
    <a href="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/security.yml"><img src="https://github.com/tasnimamin38/toolixa-agents/actions/workflows/security.yml/badge.svg?branch=main" alt="Dependency security status" /></a>
    <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
    <img src="https://img.shields.io/badge/Architecture-Local--first-16A085" alt="Local-first architecture" />
    <img src="https://img.shields.io/badge/Stage-Experimental-orange" alt="Experimental alpha" />
    <img src="https://img.shields.io/badge/License-Not%20selected-lightgrey" alt="No license selected" />
  </p>

  <p>
    <a href="https://toolixa-agents.vercel.app/">Live Agent Directory</a> ·
    <a href="#architecture">Architecture</a> ·
    <a href="#quick-start">Quick start</a> ·
    <a href="https://github.com/tasnimamin38/toolixa-agents/blob/main/docs/gateway-guide.md">Gateway guide</a> ·
    <a href="#roadmap">Roadmap</a>
  </p>
</div>

---

## Project at a glance

Toolixa Agents is evolving from a static agent directory and Python starter SDK into a **local-first AI gateway and agent runtime**. You bring the provider accounts, API credentials and machine or server that runs the agents. Toolixa provides the modular contracts and control layers.

| Principle | What it means |
|---|---|
| **BYOK** | Use API keys and accounts from providers you choose |
| **BYOR** | Run the gateway and agents in an environment you control |
| **Python-first** | Agent logic, gateway, orchestration and policy are Python |
| **Modular** | Providers, tools, memory and agents are separate integration surfaces |
| **Deny by default** | Declared capabilities do not automatically grant permissions |

## Current project status

<div align="center">
  <h3>EXPERIMENTAL MODEL-DRIVEN AGENT ALPHA · REVIEW PENDING</h3>
  <p><strong>Bounded tool-calling runtime · 13 agents · fixed engineering workflow · independent security review pending</strong></p>
</div>

**Main-branch rule:** `main` is the canonical integration branch. All work in this upgrade is maintained on a branch descended from `main` and reviewed through Draft [Pull Request #1](https://github.com/tasnimamin38/toolixa-agents/pull/1). The 13-agent capability upgrade, advanced shared tools, Gateway and GitHub-hosted runner are **not merged or deployed to the live site** until that PR is reviewed and merged.

The current feature branch upgrades the six original starters into the shared model-driven runtime, retains six domain specialists and the fixed three-stage engineering workflow, and adds a catalogue-bound GitHub Actions runner. Every model-driven agent requires at least one successful registered tool call before it can report success. The latest verified GitHub-hosted suite passed 112 tests; the independent security review and actual remote-model invocation remain outstanding.

| Area | Current state |
|---|---|
| Canonical integration branch | `main` |
| Expert-agent upgrade | Draft PR #1, descended from `main` |
| Shared model-driven runtime and evidence gate | Draft PR #1 |
| 13 catalogued agent definitions | Draft PR #1 |
| Advanced domain-analysis tools | Draft PR #1 |
| Manual GitHub-hosted Agent runner | Draft PR #1; requires a remote HTTPS BYOK endpoint |
| Local AI Gateway | Draft PR #1; single-user loopback alpha |
| Write/execute sandbox | Not enabled |
| Independent security review | Pending |
| Production multi-user SaaS | Not started |

This is **not production-ready software**. The gateway is a single-user, loopback-only local alpha. Do not expose it to the public internet or use it as an unreviewed executor for untrusted code.

## What is included

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>01 · Agent SDK</h3>
      Shared Python contracts, request/result models, execution budgets, provider and tool interfaces, policy checks and memory abstractions.
    </td>
    <td width="33%" valign="top">
      <h3>02 · Local AI Gateway</h3>
      Browser dashboard, encrypted local provider credentials, model discovery, chat playground and a compatible local API.
    </td>
    <td width="33%" valign="top">
      <h3>03 · Safety primitives</h3>
      Deny-by-default permissions, one-time approvals, secret redaction and a disabled-by-default process executor.
    </td>
  </tr>
  <tr>
    <td valign="top">
      <h3>04 · Thirteen agents</h3>
      Six bounded starters, six model-driven specialists and one fixed multi-agent engineering workflow.
    </td>
    <td valign="top">
      <h3>05 · Provider flexibility</h3>
      Connect any trusted upstream that implements the supported OpenAI Chat Completions-compatible API surface.
    </td>
    <td valign="top">
      <h3>06 · Quality gates</h3>
      Automated tests, Ruff, compile checks, catalog validation and dependency auditing in GitHub Actions.
    </td>
  </tr>
</table>

## Expert agent directory

All 12 specialist agents use the same model-driven runtime and require at least one successful registered tool call before reporting success. The thirteenth entry is a fixed sequential workflow over three real specialists. Agent definitions, registered tools, catalog metadata and tests are kept together in this repository.

| Agent | Expert task capability | Current hard boundary |
|---|---|---|
| **Dev Copilot** | Repository mapping, cross-file search, Python AST/module graph analysis, Git diff interpretation and implementation planning | Read-only; no edits, shell or code execution |
| **Aegis Security** | Passive secret-pattern and Python AST security analysis, including unsafe deserialization, shell execution and weak crypto patterns | Not an active scanner, exploit tool or penetration test |
| **Task Orchestrator** | Complex task decomposition, dependency DAG validation, critical-path schedule, slack and owner workload analysis | Plans only; does not execute or spawn agents |
| **RAG Chatbot** | Local document retrieval, multi-source synthesis and exact file/line citations | Lexical retrieval; no embeddings/vector index or web search |
| **Content Maestro** | Editorial strategy, local-source coverage, script timeline, hook cadence and CTA checks | Does not fetch external sources or predict real audience retention |
| **Web Scraper** | Local HTML extraction and bounded multi-page crawling of an offline snapshot, including internal link graphs | Zero network requests; not a live web crawler |
| **Software Engineer** | Architecture mapping, source tracing, Python AST/module inspection, Git diff and implementation/migration plans | Does not apply patches or execute code |
| **Code Reviewer** | Independent diff review, correctness/security/reliability risk ranking and test-gap analysis | Does not modify code or run tests |
| **Test Engineer** | Source-to-test mapping, pytest scenario design, fixtures, edge cases and regression strategy | Does not create or execute tests |
| **Data Analyst** | Bounded CSV profiling, types, missingness, duplicates and descriptive statistics | No raw-row export or data mutation |
| **API Architect** | OpenAPI 3.x JSON inspection, operation/schema inventory and backwards-compatibility comparison | No remote calls, YAML parsing or `$ref` dereferencing |
| **Research Analyst** | Local-document evidence retrieval, contradiction analysis, synthesis and source/line citations | No public internet browsing |
| **Engineering Workflow** | Fixed Software Engineer → Code Reviewer → Test Engineer sequence with shared budgets and evidence handoffs | Read-only, fixed order; no dynamic spawning |

### GitHub-hosted agent execution

The feature branch includes a manual Actions workflow that runs a selected catalogue Agent on a fresh GitHub-hosted runner. It is restricted to the reviewed `main` ref, grants only registered read capabilities, and never runs on pull-request jobs with provider secrets. Configure a remote HTTPS OpenAI Chat Completions-compatible endpoint with repository Variables `TOOLIXA_GATEWAY_URL`, `TOOLIXA_MODEL` and Secret `TOOLIXA_API_KEY` after the feature is merged. A laptop `localhost` Gateway is deliberately rejected.

See the [GitHub Cloud Runner guide](docs/github-cloud-runner-guide.md) for setup, workflow inputs, security limits and troubleshooting. The live Vercel directory remains unchanged until the Draft PR is merged and deployed.

## Architecture

The diagram shows the Gateway and model-driven specialist runtime on Draft PR #1. The six-agent foundation is on `main`; MCP, browser automation and isolated write/execute tools remain future integrations.

```mermaid
flowchart LR
    subgraph LOCAL["Your computer · Python runtime"]
      UI["Browser dashboard"]
      API["Toolixa Gateway API"]
      VAULT[("Encrypted local vault")]
      DB[("Local SQLite")]
      UI --> API
      API <--> DB
      DB --> VAULT
    end

    CLIENT["OpenAI-compatible client"] -->|"Bearer Toolixa key"| API
    API --> ROUTER["Provider HTTP adapter"]
    ROUTER --> MODEL["Your configured model endpoint"]

    RUNTIME["ToolAgent runtime"] --> API
    TOOLS["13 agents · registered read-only tools"] --> RUNTIME
    MCP["MCP servers and tools"] -. "future Phase 2" .-> RUNTIME
```

### Local gateway request flow

1. Start the gateway from PowerShell.
2. Open the local dashboard in your browser.
3. Add a provider name, API base URL and provider credential.
4. Test the connection and discover available models.
5. Use the playground or create a Toolixa API key.
6. Connect a compatible client to the local `/v1` endpoint.

## Provider compatibility

The Local AI Gateway adapter on Draft PR #1 supports the **OpenAI Chat Completions-compatible** model listing, JSON chat and streaming chat surface. This is a compatibility boundary, not a claim that every vendor-native API is already implemented.

| Provider or runtime | Connection approach |
|---|---|
| OpenRouter | OpenAI-compatible API endpoint |
| Ollama | Its OpenAI-compatible local endpoint |
| LM Studio | Its local OpenAI-compatible server |
| vLLM | Its OpenAI-compatible server |
| Other gateways and hosted/local models | Any trusted endpoint implementing the supported routes |
| Native Anthropic / Gemini APIs | Planned dedicated adapters |
| MCP servers | Planned Python MCP client and permission-aware tool bridge |

See [Provider and Gateway setup](https://github.com/tasnimamin38/toolixa-agents/blob/main/docs/gateway-guide.md) for endpoint requirements and limitations.

## Quick start

### 1. Install the core SDK

Requirements: Python 3.11+ and Git.

```powershell
git clone https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ./core
```

### 2. Run a bounded starter agent

For example, the read-only Dev Copilot:

```powershell
cd agents/01-dev-copilot
python main.py --workspace C:\path\to\your\project
```

Each agent has its own README, manifest and dependency file. Review its exact scope before running it.

### 3. Run the Local AI Gateway

The gateway and specialist runtime are currently on [Draft PR #1](https://github.com/tasnimamin38/toolixa-agents/pull/1), not on the default `main` branch yet. From the repository you already cloned in step 1, switch to the feature branch and install both optional extras:

```powershell
git fetch origin feature/python-local-ai-gateway
git switch feature/python-local-ai-gateway

python -m pip install --upgrade pip
python -m pip install -e ".\core[gateway,runtime]"
python -m toolixa_core.gateway
```

The terminal prints a one-time dashboard password. Open `http://127.0.0.1:20128` in your browser. The compatible API base is `http://127.0.0.1:20128/v1`.

The gateway binds to loopback only. **Do not port-forward, tunnel or reverse-proxy this experimental service to the public internet.**

### 4. Run an advanced model-driven specialist

Install the optional runtime extra and set the Toolixa Gateway key and chosen namespaced model in PowerShell:

```powershell
python -m pip install -e ".\\core[runtime]"

$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"

python agents/07-software-engineer/main.py "Map this codebase and propose a safe refactor" --workspace C:\\path\\to\\repo --grant workspace.read
```

Choose a model that supports function/tool calling. The API key is a Toolixa Gateway client key, not the upstream provider key. The Gateway keeps the upstream key in its encrypted local vault. See the [Advanced Specialist Agents guide](https://github.com/tasnimamin38/toolixa-agents/blob/main/docs/advanced-agents-guide.md).

## Security and credential handling

- Provider API keys are encrypted in the local SQLite store. The vault key is kept separately in the user's application-data directory.
- Toolixa API keys are displayed once and stored as hashes.
- The dashboard is protected by a local password and a signed session cookie.
- The local gateway rejects non-loopback plaintext HTTP endpoints and does not follow provider redirects.
- The specialist runtime validates tool schemas, enforces explicit workspace.read grants and applies request step/tool/wall-time budgets.
- Advanced agents are read-only: no source writes, arbitrary shell, test execution, browser automation, internet fetches or MCP tool invocation.
- The only multi-agent coordination is the fixed Engineer → Reviewer → Test Engineer workflow; it shares one budget and cannot spawn or reorder agents.
- No real provider key or paid model request is required for installation or automated tests.
- The gateway has not yet completed an independent penetration test or full production web-security review.
- A configured provider receives the prompts and conversation data sent to it. Review that provider's privacy, retention and billing terms.

### 5. Run the Engineering Workflow Orchestrator

This runs the existing three engineering specialists in order. Set the Gateway environment variables from step 4 first:

```powershell
python agents/13-engineering-workflow/main.py "Review the payments service and propose the safest reliability improvement" --workspace C:\\path\\to\\repo --grant workspace.read
```

The final JSON contains the Software Engineer analysis, independent Code Reviewer findings, Test Engineer plan and one aggregate budget report. Every stage must use a real read-only tool. The workflow stops on stage failure or exhausted budget; it does not change source files or run tests. See the [Engineering Workflow guide](docs/engineering-workflow-guide.md).

Read the [Security Model](docs/security-model.md) before connecting credentials or enabling any additional capabilities.

## Roadmap

| Phase | Objective | Status |
|---|---|---|
| **0 · Foundation** | Python core, six bounded starter agents, static directory, CI | <strong>Completed</strong> |
| **1 · Gateway + Specialist Runtime** | Encrypted BYOK Gateway, model tool-call runtime, six advanced specialists and fixed engineering workflow | <strong>Draft PR #1; validation and security review pending</strong> |
| **2 · Native AI + MCP** | Native provider adapters, MCP registration/discovery and permission-gated tool calls | Planned |
| **3 · Advanced Agent Runtime** | Multi-agent delegation, persistent memory, browser integration and reviewed patch/execute sandbox | Planned |
| **4 · Production Gate** | Threat-model review, penetration testing, rate limits, audit, egress and operational controls | Not started |
| **5 · Hosted Service** | Optional multi-user SaaS, tenant isolation, remote secrets, quotas and billing | Not started |

### When does Experimental end?

Experimental status does not end just because the dashboard or API exists. The project moves out of experimental only after the agents perform their documented jobs reliably, provider and MCP integrations pass adversarial testing, tool execution is isolated, credentials and tenants are protected, and an independent security review plus release acceptance tests are complete.

Until those conditions are met, the honest project status remains **Experimental**.

## Development and verification

For the current `main` foundation, install the core SDK and development tools:

```powershell
python -m pip install -e ./core
python -m pip install -r agents/06-web-scraper/requirements.txt
python -m pip install "pytest>=9.0.3,<10" "ruff>=0.8,<1"

python -m compileall -q core/src agents scripts tests
ruff check core/src agents scripts tests
ruff format --check core/src agents scripts tests
python scripts/build_catalog.py --check
python -m pytest -q
```

To run the Local AI Gateway and model-driven specialists, first check out the feature branch using the instructions above, then install `python -m pip install -e "./core[gateway,runtime]"`. Gateway and workflow contract tests use mocked upstream responses and do not make paid provider calls.

## Documentation

| Document | What it covers |
|---|---|
| [Architecture](docs/architecture.md) | Components, boundaries and data flow |
| [Security Model](docs/security-model.md) | Permissions, secrets, execution and threats |
| [Gateway Guide](https://github.com/tasnimamin38/toolixa-agents/blob/main/docs/gateway-guide.md) | Local dashboard, providers and compatible API (Draft PR #1) |
| [BYOR / BYOK Guide](docs/byor-guide.md) | Runtime and credentials ownership |
| [Installation](docs/installation.md) | Install and launch |
| [Development](docs/development.md) | Tests, lint, CI and contribution workflow |
| [Advanced Specialist Agents](https://github.com/tasnimamin38/toolixa-agents/blob/main/docs/advanced-agents-guide.md) | Model setup, tool capabilities, PowerShell usage and limits |
| [Engineering Workflow](docs/engineering-workflow-guide.md) | Fixed three-stage handoffs, shared budget, CLI and security boundaries |
| [Workflow Design](docs/specs/2026-11-28-multi-agent-engineering-workflow-design.md) | Workflow contract, handoffs, trust and release limits |
| [Workflow Implementation Plan](docs/plans/2026-11-28-multi-agent-engineering-workflow.md) | Test-first tasks and release gates |
| [Advanced Runtime Design](https://github.com/tasnimamin38/toolixa-agents/blob/main/docs/specs/2026-11-27-advanced-agent-runtime-design.md) | Shared runtime, tool policies and test boundaries |
| [Advanced Runtime Plan](https://github.com/tasnimamin38/toolixa-agents/blob/main/docs/plans/2026-11-27-advanced-agent-runtime.md) | Implementation tasks and release gates |
| [Foundation Plan](docs/plans/2026-11-27-toolixa-agents-implementation.md) | Original six-agent foundation plan |

## License

No license has been selected. Public visibility on GitHub does not grant permission to reuse, modify or redistribute this project. Do not assume an open-source license applies.

---

<div align="center">
  <strong>Toolixa Agents</strong><br/>
  <sub>Local-first · Python-first · Your models · Your runtime · Your control</sub><br/><br/>
  <a href="https://github.com/tasnimamin38/toolixa-agents">Repository</a> ·
  <a href="https://toolixa-agents.vercel.app/">Agent Directory</a> ·
  <a href="https://github.com/tasnimamin38/toolixa-agents/pulls">Pull requests</a>
</div>