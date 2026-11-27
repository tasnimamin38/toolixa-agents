# Toolixa Agent Ecosystem — Architecture Design

**Status:** Architecture approved; written specification awaiting user review  
**Date:** 2026-11-27  
**Current repository:** `tasnimamin38/toolixa-web-scraper`  
**Target repository name:** `tasnimamin38/toolixa-agents`  
**Default branch:** `main`  
**License decision:** No license file for the initial build; licensing remains on hold

## 1. Purpose

Toolixa is a source-code directory and modular ecosystem for independent, developer-operated AI agents. It is not a centrally hosted agent runtime. Developers obtain agent source code, configure their own model/provider credentials, choose an execution runtime, and run agents in environments they control.

The first release establishes six agent packages—Dev Copilot, Aegis Security, Task Orchestrator, RAG Chatbot, Content Maestro, and Web Scraper—on top of a small shared Python SDK and a static web directory.

The architecture must allow an agent to be installed and run independently while still reusing shared contracts, provider adapters, policy interfaces, and utilities when the developer has the complete monorepo or a packaged release.

## 2. Product and architecture principles

1. **BYOR (Bring Your Own Runtime):** the user selects and operates the execution environment. Toolixa does not require a hosted execution service.
2. **BYOK (Bring Your Own Key):** model/search provider credentials belong to the user and are injected at runtime. Toolixa does not collect or store them.
3. **Local-first by default:** memory, files, logs, and artifacts remain in the configured local workspace unless an agent explicitly integrates with an external service.
4. **Modular monorepo:** shared interfaces are maintained once; each agent has its own manifest, documentation, tests, and direct dependencies.
5. **Least privilege:** agents receive only the file, network, and tool permissions explicitly granted for a run.
6. **Safe defaults:** shell execution, arbitrary network access, destructive file operations, and active security testing are disabled unless an operator enables a narrowly scoped policy.
7. **Provider neutrality:** core contracts do not depend on one LLM vendor or one agent framework.
8. **Inspectable behavior:** manifests, permission requests, execution budgets, and audit events are visible to the operator.
9. **No pretend isolation:** a Python process or a Docker container alone is not described as a complete security boundary.
10. **Static catalog, separate execution:** the website lists and documents agents; it does not execute Python agents.

## 3. Scope

### 3.1 Initial release includes

- A static Agent Directory at the repository root.
- A catalog generated from each agent's `agent.json` manifest.
- A lightweight, installable shared package named `toolixa-core`.
- Six agent directories with documented entry points and separate dependency lists.
- Common request/result, provider, tool, policy, approval, execution, configuration, and logging contracts.
- Safe starter behavior and focused tests for each initial agent.
- Documentation for installation, BYOR, provider configuration, security, and contribution.
- Continuous integration for Python tests, formatting/linting, manifest validation, and dependency/security checks.

### 3.2 Explicitly out of scope for the first release

- A Toolixa-hosted model inference service.
- A central user database, billing, subscriptions, account management, or multi-tenant SaaS backend.
- A remote job scheduler or hosted agent execution service.
- Automatic approval of shell, filesystem, network, or security-testing actions.
- A promise that any agent can safely execute arbitrary untrusted code on a general-purpose host.
- A mandatory dependency on LangChain, LangGraph, AutoGen, ChromaDB, Docker, or a paid API.
- Publishing packages to PyPI before package metadata, release process, and ownership are reviewed.

## 4. System context and data flow

```text
Developer / Operator
    |
    +--> Toolixa Agent Directory (static HTML + generated catalog)
    |
    +--> Selects and downloads an agent source package
              |
              +--> Installs agent-specific dependencies
              |
              +--> Installs toolixa-core (when the agent uses shared contracts)
              |
              +--> Supplies provider credentials through local environment
              |
              +--> Selects local runtime and grants explicit permissions
                          |
                          v
                  Agent entry point
                          |
              +-----------+------------+
              |                        |
         Provider adapter          Tool registry
              |                        |
          User's model          Policy / approval gate
                                       |
                                Runtime adapter
                                       |
                             User-controlled executor
                                       |
                              Result + audit events
```

The static website and agent runtime are independent. A website outage must not prevent an already-installed agent from running. A model provider outage must return a bounded provider error, not bypass policy or switch to an unapproved provider.

## 5. Repository layout

The following is the target layout. Paths are proposed until created and validated.

```text
toolixa-agents/
├── index.html
├── vercel.json
├── README.md
├── pyproject.toml
├── .gitignore
├── catalog/
│   └── agents.json                  # generated; do not edit by hand
├── core/
│   ├── pyproject.toml
│   └── src/toolixa_core/
│       ├── contracts/
│       │   ├── agent.py
│       │   ├── request.py
│       │   └── response.py
│       ├── providers/
│       │   ├── base.py
│       │   ├── factory.py
│       │   └── registry.py
│       ├── memory/
│       │   ├── base.py
│       │   └── models.py
│       ├── tools/
│       │   ├── base.py
│       │   └── registry.py
│       ├── security/
│       │   ├── policy.py
│       │   ├── approvals.py
│       │   └── permissions.py
│       ├── runtime/
│       │   ├── executor.py
│       │   └── limits.py
│       ├── config.py
│       └── logging.py
├── agents/
│   ├── 01-dev-copilot/
│   ├── 02-aegis-security/
│   ├── 03-task-orchestrator/
│   ├── 04-rag-chatbot/
│   ├── 05-content-maestro/
│   └── 06-web-scraper/
├── docs/
│   ├── architecture.md
│   ├── security-model.md
│   ├── byor-guide.md
│   ├── installation.md
│   └── development.md
├── tests/
│   ├── core/
│   ├── contracts/
│   └── integration/
├── scripts/
│   └── build_catalog.py
└── .github/workflows/
    ├── ci.yml
    └── security.yml
```

Each agent directory contains, at minimum:

```text
agent-folder/
├── main.py
├── agent.json
├── requirements.txt
├── README.md
├── .env.example
└── tests/
```

An agent may add focused modules such as `prompts/`, `adapters/`, or `sub_agents/`. It must not silently add global dependencies to other agents.

## 6. Shared core package

### 6.1 Packaging boundary

- The import package is `toolixa_core`; the distribution name is `toolixa-core`.
- Core targets Python 3.11 or newer.
- Core runtime dependencies are limited to Python standard-library functionality wherever practical.
- Provider SDKs, vector databases, browser automation, and orchestration frameworks are optional extras or agent-specific dependencies.
- Core does not read arbitrary `.env` files from unknown directories. Each agent documents its configuration source and loads only the explicitly selected file or environment.
- The monorepo development install is `python -m pip install -e ./core`.
- A standalone agent bundle must include a compatible core package or install a pinned core release/source reference. A folder copied without its declared core dependency is not considered a complete standalone distribution.
- The initial release may be installed from the monorepo; PyPI publishing is a later release decision.

### 6.2 Core modules and responsibilities

| Module | Responsibility | Must not do |
|---|---|---|
| `contracts` | Shared typed request, result, manifest, and event models | Execute tools or call providers |
| `providers` | Provider protocols, adapter registration, and selection | Store credentials or choose a provider without configuration |
| `memory` | Storage/retrieval interfaces and metadata contracts | Require a hosted database |
| `tools` | Tool protocol, metadata, argument schema, and registry | Grant permissions implicitly |
| `security` | Permission policy, approval request, and policy decision contracts | Claim to sandbox a process |
| `runtime` | Executor protocol, execution result, timeout and resource-limit models | Run commands in-process by default |
| `config` | Typed configuration loading and validation | Log secret values |
| `logging` | Structured, redacted operational events | Record API keys, credentials, or raw secret-bearing environment |

### 6.3 Shared contracts

The first implementation must define stable typed equivalents of the following conceptual models:

**AgentRequest**
- `request_id`: unique request identifier.
- `agent_id`: manifest identifier of the target agent.
- `input`: agent-specific JSON-compatible input.
- `workspace`: explicitly selected workspace path or logical workspace handle.
- `grants`: permission grants available for this request.
- `budget`: step, wall-time, and tool-call limits.
- `trace_id`: correlation identifier for logs and events.

**AgentResult**
- `request_id` and `agent_id`.
- `status`: `succeeded`, `failed`, `cancelled`, or `needs_approval`.
- `output`: JSON-compatible result data.
- `artifacts`: workspace-relative artifact references.
- `usage`: provider and execution usage when reported.
- `diagnostics`: redacted, structured error information.

**ToolCallContext**
- Request and trace identifiers.
- Granted capabilities and allowed workspace roots.
- Network policy and execution budget.
- An approval verifier for actions requiring approval.
- Secret access through named, scoped secret references; never through serialized request logs.

All contract models must be serializable without leaking credentials. Unknown fields must not silently grant a capability.

### 6.4 Provider adapters

Core defines protocols and a registry, not a universal model implementation. The first provider adapters may cover OpenAI-compatible APIs, Anthropic, and local Ollama, but each adapter is optional and tested independently.

The provider contract must expose bounded operations such as text generation and, where supported, embeddings. Provider-specific features remain behind adapter capability declarations. An unsupported capability returns a typed unsupported-capability error rather than silently degrading.

Provider credentials are injected through environment variables or a user-controlled secret manager. They are never written to manifests, source files, catalog data, logs, traces, or generated reports.

### 6.5 Memory interfaces

Memory is an adapter boundary, not a mandatory database. Initial interfaces cover document records, chunks, embeddings, metadata filters, and retrieval results. Local filesystem or SQLite storage may be used for the first local implementation. ChromaDB or another vector store remains optional.

The RAG agent must retain source references for retrieved chunks. Retrieved document text is untrusted content and must never be interpreted as system-level instructions.

## 7. Agent manifest and discovery

Each agent provides an `agent.json` manifest. The manifest is the source of truth for discovery and is validated in CI.

Required manifest fields:

| Field | Meaning |
|---|---|
| `schema_version` | Version of the manifest schema |
| `id` | Stable, lowercase agent identifier |
| `name` | Display name |
| `version` | Agent release version |
| `category` | Directory category |
| `description` | Concise, accurate summary |
| `entrypoint` | Relative entry point, initially `main.py` |
| `python` | Supported Python version range |
| `dependencies` | Agent-specific dependency declarations |
| `capabilities` | Declared functions offered by the agent |
| `permissions` | Permission names the agent may request |
| `status` | `experimental`, `beta`, or `stable` |
| `documentation` | Relative README path |

The manifest does not grant permissions. It only declares what the agent may request. The runtime operator's policy determines the actual grants.

`scripts/build_catalog.py` validates manifests and generates `catalog/agents.json` deterministically. It rejects duplicate agent IDs, invalid relative paths, malformed versions, unsupported permission names, and missing README or entry-point files. It must not execute agent code while building the catalog.

## 8. Security and permission model

### 8.1 Permission model

Permissions are explicit, narrow, and request-scoped. Initial permission families are:

- `workspace.read`: read only within declared workspace roots.
- `workspace.write`: write only within declared workspace roots.
- `network.http`: outbound HTTP under an explicit host and address policy.
- `process.execute`: execute a declared command through a configured executor.
- `browser.automate`: browser automation through an explicitly configured browser runtime.
- `security.scan.passive`: passive analysis of supplied files or explicitly authorized assets.
- `security.scan.active`: active testing against explicitly authorized targets, disabled by default.
- `provider.invoke`: invoke only the provider selected by the operator.
- `memory.read` and `memory.write`: access the configured memory namespace.

A permission decision is deny-by-default. The agent manifest cannot elevate its own grant. A user approval is bound to an action, target, workspace, and short validity period; an approval for one action cannot authorize unrelated future actions.

### 8.2 Execution isolation

- Core exposes an executor protocol; it does not run untrusted code in the agent process.
- The default executor is disabled for arbitrary shell execution.
- Any enabled executor must use a separately configured isolation boundary and enforce timeout, memory, CPU, process-count, filesystem, and network constraints where supported.
- Rootless containers, restricted containers, gVisor, or microVM-based execution may be provided as adapters. The selected adapter's guarantees and limitations must be documented.
- Container use alone is not represented as a complete security boundary. Host mounts, Docker socket access, privileged mode, host networking, and inherited secrets are prohibited by default.
- Destructive or externally visible actions require a separate approval decision and produce an audit event.

### 8.3 Web Scraper network protections

The Web Scraper must defend against SSRF and DNS-rebinding-style bypasses. The HTTP layer must:

- accept only explicitly supported schemes, initially HTTP and HTTPS;
- reject loopback, private, link-local, multicast, unspecified, reserved, and cloud metadata destinations after DNS resolution;
- validate every resolved address and every redirect destination;
- enforce redirect and response-size limits;
- prevent proxy environment variables from bypassing the configured network policy;
- use connection and overall timeouts;
- avoid forwarding credentials or cookies to a different origin;
- restrict downloads and output writes to the selected workspace;
- return a typed blocked-target error when a destination violates policy.

The implementation must account for DNS resolution and the actual connected peer so validation is not limited to the hostname string. Browser automation, when added, must use an equivalent network boundary; validating only the initial URL is insufficient.

### 8.4 Aegis Security authorization

Aegis starts with local, passive analysis of user-supplied repositories and artifacts. Active scanning requires an explicit target allowlist and a separate active-scan grant. It must not scan arbitrary public hosts or expand its scope based on discovered links.

### 8.5 Secret handling and audit

- `.env.example` contains placeholders only.
- Real `.env` files, private keys, tokens, cookies, and provider credentials are ignored by Git.
- Logs redact known secret patterns and never include full environment dumps or authorization headers.
- Audit events record who/what requested an action, the policy result, target, time, and outcome without capturing secret values.
- The project does not claim that local logs are tamper-proof.

## 9. Initial agent responsibilities

### 9.1 01-dev-copilot

Workspace-aware coding assistance, repository inspection, proposed multi-file edits, test generation, and test-result summarization. Applying edits and executing commands require explicit workspace and execution grants. Self-correction is limited to a configured number of attempts and cannot bypass test, approval, or resource limits.

### 9.2 02-aegis-security

Local source inspection, secret-pattern checks, dependency audit integration, and passive security findings. Each finding includes file/line or package evidence, severity, confidence, and recommended remediation. Active testing is disabled unless separately authorized.

### 9.3 03-task-orchestrator

A bounded state machine that decomposes tasks, schedules approved sub-agent calls, tracks dependencies, aggregates results, and records failures. It enforces maximum steps, depth, concurrency, wall time, and spend/usage budgets. Sub-agents receive only the grants explicitly delegated to them; the orchestrator cannot create broader permissions.

LangGraph may be an optional adapter. A small native state-machine implementation is preferred for the initial baseline so the core is not coupled to a framework.

### 9.4 04-rag-chatbot

Local document ingestion, chunking, embedding through a selected provider, retrieval, and answers with source references. The user selects supported file types and workspace roots. The agent must report when no supporting source is found rather than fabricate a citation.

### 9.5 05-content-maestro

Research and content generation through selected search and LLM provider adapters. It distinguishes sourced facts from editorial suggestions, records source URLs and retrieval dates, and does not claim live research when no search provider is configured. SEO scoring is advisory, not a guarantee of search ranking.

### 9.6 06-web-scraper

Configurable page fetching, HTML parsing, extraction of page metadata and links, bounded pagination/crawling, and structured JSON output. It supports static HTML first. Browser rendering is an optional future adapter with separate dependencies and network policy. It does not bypass authentication, paywalls, bot controls, or access restrictions.

## 10. Static Agent Directory and Vercel

- `index.html` is the static website entry point.
- The page reads the generated `catalog/agents.json` from the same origin and renders category-filterable agent cards.
- Each card links to the matching agent folder and README in the GitHub repository.
- A visible fallback state explains when the catalog cannot be loaded.
- No Python runtime, API route, database, or server-side agent execution is deployed to Vercel.
- The site must remain usable on mobile and desktop and meet basic keyboard, contrast, and semantic HTML accessibility expectations.
- `vercel.json` is included only for valid, necessary static routing or response-header configuration; it must not invent a Python entry point or serverless runtime.
- Every catalog link is checked by the catalog validation test.

## 11. Dependencies and framework policy

- Each agent owns its direct runtime dependencies in its own `requirements.txt`.
- Core's packaging metadata lives in `core/pyproject.toml`.
- The root `pyproject.toml` configures repository-wide development tools and test discovery; it does not turn every agent dependency into a mandatory global dependency.
- Heavy optional libraries are not imported from core at module import time.
- LangChain, LangGraph, AutoGen, ChromaDB, Playwright, and cloud SDKs are optional integrations, not global prerequisites.
- Dependency versions are constrained and reviewed; CI audits for known vulnerabilities.
- A minimal installation of one agent must not require installing dependencies for the other five agents.

## 12. Testing and quality gates

The initial CI workflow must run on pull requests and pushes to the primary branch.

Required checks:

1. Manifest schema and catalog generation validation.
2. Python syntax/compile checks for core and each agent.
3. Core contract and policy unit tests.
4. Agent-specific unit tests using mocked providers and mocked external HTTP.
5. SSRF regression tests covering loopback, private IPv4/IPv6, link-local, metadata destinations, redirects, mixed DNS answers, and blocked schemes.
6. Permission tests proving undeclared or ungranted operations are denied.
7. Secret-redaction tests using synthetic credentials.
8. Static catalog link and required-file checks.
9. Formatting/lint checks.
10. Dependency vulnerability audit.

No CI test may make an uncontrolled request to an arbitrary external target or require a paid provider key. Integration tests that need a real provider or network are opt-in and clearly separated.

## 13. Documentation requirements

- Root README: product purpose, agent directory, supported model/runtime concept, quick start, security warning, contribution link, and license status.
- `docs/architecture.md`: system boundaries, package layout, contracts, and data flow.
- `docs/security-model.md`: permissions, approval behavior, executor guarantees, threat model, and limitations.
- `docs/byor-guide.md`: supported installation and runtime choices, local configuration, and provider setup.
- `docs/installation.md`: install one agent and its core dependency without installing every agent's dependencies.
- `docs/development.md`: repository setup, testing, catalog generation, and contribution process.
- Each agent README: purpose, requirements, supported capabilities, permissions requested, configuration, invocation, outputs, limitations, and tests.

Documentation must distinguish implemented features from planned adapters. No documentation may describe a starter scaffold as a production-ready autonomous agent.

## 14. Repository naming and migration

The repository has been renamed in GitHub settings from `tasnimamin38/toolixa-web-scraper` to `tasnimamin38/toolixa-agents`. The GitHub repository ID and `main` branch history were preserved. The canonical URL is now:

`https://github.com/tasnimamin38/toolixa-agents`

The GitHub settings UI confirmed that the new name was available and that the repository page loaded under the new canonical name after the rename. GitHub normally redirects old repository URLs, but downstream integrations still require verification.

The implementation updates catalog, README, and website links to the canonical repository name. Vercel Git integration and any existing local clone remotes must be checked by their operators; this repository change does not by itself prove those integrations are connected or deployed.

## 15. Licensing and source availability

The user explicitly chose to hold the license decision. Therefore:

- Do not create a `LICENSE` file in the initial architecture implementation.
- Do not add an SPDX license identifier or claim that the code is Apache-2.0, MIT, or otherwise open-source.
- Documentation must state that no license has been selected and that public visibility does not itself grant permission to reuse, modify, or redistribute the code.
- Revisit licensing only after the repository owner makes a separate decision.

## 16. Rollout and acceptance criteria

The implementation is accepted only when all of the following are true:

- The repository has the approved modular structure and no mandatory dependency shared across all agents except the small core package.
- Core installs as a Python package and exposes tested contracts, provider/tool interfaces, policy decisions, and executor limits.
- All six agent manifests validate and generate one deterministic catalog.
- Each agent has a documented entry point, isolated dependencies, explicit permissions, and focused tests.
- Permission denial is enforced before tool execution.
- Arbitrary shell execution is disabled by default.
- Web Scraper SSRF tests demonstrate blocking of forbidden destinations and redirects.
- RAG and other provider-backed behavior fail clearly when a provider is not configured.
- The static website loads the catalog and links to the correct agent documentation.
- CI passes without paid API keys or uncontrolled external scans.
- Vercel deployment remains static and does not attempt to execute Python agents.
- Repository rename is confirmed before new canonical repository links are published.
- No license file or license claim is introduced.

## 17. Known trade-offs

- A monorepo makes shared changes easier but requires clear ownership and test boundaries to prevent agent coupling.
- A shared SDK improves consistency but creates a version compatibility requirement for independently distributed agent folders; standalone bundles must pin a compatible core version.
- A static catalog is inexpensive and reliable but does not provide user accounts, hosted execution, or dynamic agent telemetry.
- Local-first memory gives the operator control but requires the operator to manage backups and storage lifecycle.
- Safe execution isolation depends on the configured host runtime; the repository can define interfaces and safe defaults but cannot guarantee the security of every user environment.
- Keeping licensing on hold preserves the owner's current decision but means the repository must not market itself as an OSI-approved open-source project.

## 18. Spec review checklist

- [x] BYOR and BYOK are separate concepts.
- [x] Website hosting is separate from agent execution.
- [x] Core and agent dependencies have explicit ownership boundaries.
- [x] Agent manifests declare capabilities but cannot grant permissions.
- [x] Shell, browser, network, and active security actions have explicit policy gates.
- [x] SSRF defenses cover DNS resolution and redirect destinations.
- [x] Provider secrets are excluded from source, manifests, logs, and catalog data.
- [x] License hold is reflected consistently.
- [x] Repository rename is not represented as complete before verification.
- [x] Initial scope excludes a hosted SaaS backend and paid runtime.
