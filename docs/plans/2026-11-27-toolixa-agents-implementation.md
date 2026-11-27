# Toolixa Agent Ecosystem Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox syntax for tracking.

**Goal:** Deliver a static agent directory and a secure, modular Python starter ecosystem with six independently documented agents.

**Architecture:** A lightweight installable toolixa-core package defines provider-neutral contracts, policy checks, approvals, tool registration, memory interfaces, and a disabled-by-default executor. Six independent agent folders consume those interfaces; a generated manifest catalog feeds a static Vercel website.

**Tech Stack:** Python 3.11+, setuptools, pytest, Ruff, BeautifulSoup for local HTML parsing, vanilla HTML/CSS/JavaScript, GitHub Actions, Vercel static deployment.

## Global Constraints

- BYOR and BYOK remain separate.
- No hosted model runtime, database, billing system, or paid API is required.
- Core has no mandatory third-party runtime dependency.
- Agent-specific dependencies remain isolated.
- Shell execution and active security scanning are disabled by default.
- Manifests declare requested capabilities but never grant permissions.
- Scraping begins with supplied local HTML; network fetching is not enabled until an address-pinned transport or enforced egress boundary is implemented and tested.
- No license file or license claim is introduced.
- Canonical repository name is toolixa-agents.

---

### Task 1: Shared SDK and governance baseline

**Files:** core/pyproject.toml, core/src/toolixa_core/**, tests/core/test_core.py, docs/architecture.md, docs/security-model.md, docs/byor-guide.md, docs/plans/2026-11-27-toolixa-agents-implementation.md, README.md, pyproject.toml, .gitignore.

**Interfaces:** Produces AgentRequest, AgentResult, ExecutionBudget, AgentManifest, ProviderRegistry, ToolRegistry, RuntimePolicy, ApprovalManager, BudgetTracker, DisabledExecutor, ToolSpec, ToolCallContext, DocumentChunk, and ToolixaSettings.

- [ ] Add and run tests for serialization, invalid budgets, artifact traversal, denied permissions, workspace boundaries, host allowlists, one-use approvals, step limits, provider selection, disabled execution, tool permission gates, and secret redaction.
- [ ] Run: python -m pip install -e ./core && python -m pytest tests/core -q
- Expected: all focused core tests pass.
- [ ] Run: python -m compileall -q core/src
- Expected: no syntax errors.
- [ ] Commit: feat: establish Toolixa shared core and safety contracts.

### Task 2: Six independent agent starters

**Files:** agents/01-dev-copilot/**, agents/02-aegis-security/**, agents/03-task-orchestrator/**, agents/04-rag-chatbot/**, agents/05-content-maestro/**, agents/06-web-scraper/**, tests/agents/test_agent_starters.py, scripts/build_catalog.py, catalog/agents.json.

**Interfaces:** Produces read-only workspace analysis, passive local security findings, deterministic task dependency ordering, local text retrieval with source ranges, evidence-aware content briefs, and local HTML extraction.

- [ ] Test all six agent behaviors with temporary local fixtures; no test may contact arbitrary external hosts or execute shell commands.
- [ ] Run: python -m pytest tests/agents -q
- Expected: all six focused tests pass, secrets are not returned in findings, DAG cycles are rejected, RAG results cite line ranges, and scraper parses supplied HTML only.
- [ ] Run: python scripts/build_catalog.py --check
- Expected: six manifests validate and generated catalog matches committed output.
- [ ] Commit: feat: add six modular Toolixa agent starters.

### Task 3: Static Agent Directory

**Files:** index.html, assets/styles.css, assets/app.js, catalog/agents.json, vercel.json.

**Interfaces:** Consumes the deterministic catalog and produces a responsive static directory with search, category filters, status labels, and GitHub source/documentation links.

- [ ] Verify catalog IDs and paths before rendering.
- [ ] Use DOM text nodes and createElement; never inject catalog values with innerHTML.
- [ ] Run: python scripts/build_catalog.py --check && python -m pytest -q
- Expected: deterministic catalog and all tests pass.
- [ ] Verify Vercel config contains static headers only and no Python runtime or function.
- [ ] Commit: feat: publish static Toolixa agent directory.

### Task 4: CI and release hygiene

**Files:** .github/workflows/ci.yml, .github/workflows/security.yml, docs/installation.md, docs/development.md.

**Interfaces:** Consumes core, manifests, agent tests, catalog, and static assets; produces repeatable pull-request quality and dependency-audit checks.

- [ ] Run: python -m compileall -q core/src agents scripts tests
- Expected: no syntax errors.
- [ ] Run: ruff check core/src agents scripts tests
- Expected: no lint findings.
- [ ] Run: ruff format --check core/src agents scripts tests
- Expected: all tracked Python files are formatted.
- [ ] Run: python scripts/build_catalog.py --check && python -m pytest -q
- Expected: all local checks pass.
- [ ] Ensure CI does not require paid provider keys or perform uncontrolled scans.
- [ ] Commit: ci: add Toolixa quality and dependency security checks.

## Completion criteria

- Exactly six validated agent manifests generate the catalog.
- Core installs and its contract/policy tests pass.
- Each agent runs its documented local starter behavior.
- The default executor always denies shell execution.
- Ungranted permissions and paths outside approved roots are denied.
- The first Web Scraper performs local HTML parsing only.
- The static directory uses safe DOM APIs and loads the generated catalog.
- CI covers tests, lint, compile, catalog consistency, and dependency auditing.
- Vercel remains static-only.
- No license file or license claim is introduced.
