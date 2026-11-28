# Unified Expert Agents and GitHub Cloud Execution Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring every catalogued Toolixa agent onto one evidence-backed model runtime and make approved agent runs execute on GitHub-hosted cloud runners rather than the user's laptop.

**Architecture:** Each agent exports a typed `AgentDefinition` with distinct domain tools and a minimum evidence requirement. A single request-scoped runtime validates tool schemas, permissions, budgets and outputs. A GitHub Actions workflow dispatches one registered agent against the checked-out repository using BYOK credentials supplied only through GitHub Secrets/Variables; the runner is ephemeral and read-only.

**Tech Stack:** Python 3.11+, existing Toolixa `ToolAgent`, OpenAI Chat Completions-compatible provider, GitHub Actions, pytest, Ruff and pip-audit.

## Global Constraints

- GitHub is the sole development workspace and persistent source of truth. No user laptop files, local Python environments, Docker containers or self-hosted runners are required or created.
- All ongoing work remains a descendant of `main` and is delivered through Pull Request #1 until the reviewed integration is ready.
- Every catalogued agent must use the shared model-driven runtime, expose a non-empty domain-specific tool set, and require at least one successful registered tool call before reporting success.
- Tool arguments are JSON-schema validated; every tool permission is checked by request-scoped policy; step, tool-call and wall-clock budgets remain enforced.
- Source-reading agents remain read-only. No arbitrary shell, source writes, patch apply, test execution, internet fetch or dynamic agent spawning is enabled by this plan.
- Model endpoints and credentials are configured as GitHub repository Variables/Secrets. Never store provider credentials in Git, workflow inputs, agent manifests, logs or artifacts.
- The cloud runner checks out only the selected reviewed repository revision, uses `permissions: contents: read`, has a fixed maximum timeout and does not expose secrets to pull-request jobs.
- Agent execution is considered unavailable until a compatible HTTPS model endpoint, model ID and API key are configured in GitHub settings; no mock response is presented as a real model run.

---

### Task 1: Enforce evidence-backed AgentDefinition execution

**Files:**
- Modify: `core/src/toolixa_core/runtime/agent.py`
- Test: `tests/core/test_agent_runtime.py`
- Modify: `agents/07-software-engineer/main.py` through `agents/12-research-analyst/main.py`
- Modify: `agents/13-engineering-workflow/main.py`

**Interfaces:**
- `AgentDefinition(..., min_tool_calls: int = 0)`
- When `min_tool_calls > 0`, a final answer with fewer successful registered tool calls returns `AgentStatus.FAILED` and diagnostic `evidence_missing`.
- Model final answers are passed through the existing credential redactor before being returned.

- [ ] Add failing tests for a no-evidence completion and a model answer containing a credential-like string.
- [ ] Observe the focused runtime tests fail for the missing minimum-evidence contract and unredacted output.
- [ ] Add validated `min_tool_calls` to `AgentDefinition`; fail closed when the model ends before the minimum number of successful tool calls.
- [ ] Redact final model answers before constructing `AgentResult`.
- [ ] Set `min_tool_calls=1` for every model-driven specialist and workflow stage.
- [ ] Run the focused runtime, specialist and workflow tests.

### Task 2: Upgrade the six original starter agents

**Files:**
- Create: `core/src/toolixa_core/agent_tools/security.py`
- Create: `core/src/toolixa_core/agent_tools/orchestration.py`
- Create: `core/src/toolixa_core/agent_tools/content.py`
- Create: `core/src/toolixa_core/agent_tools/html.py`
- Modify: `core/src/toolixa_core/agent_tools/__init__.py`
- Modify: `core/src/toolixa_core/agent_runtime_cli.py`
- Modify: `agents/01-dev-copilot/main.py` through `agents/06-web-scraper/main.py`
- Modify: `tests/agents/test_agent_starters.py`
- Test: `tests/agents/test_expert_starter_agents.py`

**Interfaces:**
- Every original agent exports `build_agent() -> AgentDefinition`.
- Domain tools are named `security.audit_source`, `orchestration.validate_task_graph`, `content.validate_editorial_brief` and `html.extract_file`.
- Existing deterministic helper functions remain callable for backward compatibility.
- The shared CLI accepts only explicitly supported permissions; Task Orchestrator does not require a workspace, while workspace tools require `workspace.read`.

- [ ] Add failing definition/tool-contract tests for all six original agents.
- [ ] Implement bounded passive security inspection that emits rule IDs, locations and descriptions, never secret values.
- [ ] Implement deterministic task-DAG validation with duplicate/missing/self dependency and cycle detection.
- [ ] Implement editorial evidence-coverage validation without claiming that URLs or source facts were fetched.
- [ ] Implement bounded local HTML extraction using the Python standard library; it must not make network requests.
- [ ] Convert the six original entrypoints to shared `ToolAgent` definitions and specialist system instructions.
- [ ] Verify each agent performs at least one real registered tool call in mocked-provider end-to-end tests.
- [ ] Run all 13 agent-definition tests, catalogue validation and regression tests.

### Task 3: Run registered agents through GitHub-hosted Actions

**Files:**
- Create: `.github/workflows/agent-run.yml`
- Create: `scripts/run_github_agent.py`
- Test: `tests/agents/test_github_agent_runner.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/security.yml`

**Interfaces:**
- Manual inputs: registered `agent_id`, task text and bounded step/tool/time limits.
- Runtime configuration: `TOOLIXA_GATEWAY_URL` and `TOOLIXA_MODEL` repository Variables; `TOOLIXA_API_KEY` repository Secret.
- The runner resolves only an allowlisted manifest/entrypoint from `catalog/agents.json`; it never evaluates user-supplied Python or command text.
- Workspace is the checked-out repository root; permission grants are derived from the selected agent's declared tool requirements.
- The first version is read-only and restricted to `main`; it writes a sanitized result to the Actions step summary and never commits changes.

- [ ] Add runner tests using injected fake clients; no real model credentials or paid inference calls are used by CI.
- [ ] Verify unknown agent IDs, missing provider configuration, oversized prompts and out-of-range budgets fail with non-zero exit codes.
- [ ] Implement the manifest-allowlisted runner and bounded result summary.
- [ ] Add a manual GitHub Actions workflow with minimal permissions, no PR secret exposure, concurrency control and a fixed timeout.
- [ ] Add workflow syntax/configuration checks to CI.
- [ ] Keep dependency audit and core mandatory-dependency checks green.

### Task 4: Documentation, catalogue and release gates

**Files:**
- Modify: `README.md`
- Modify: `docs/installation.md`
- Modify: `docs/advanced-agents-guide.md`
- Modify: `docs/security-model.md`
- Create: `docs/github-cloud-runner-guide.md`
- Modify: `catalog/agents.json` only when manifest data changes.

- [ ] Document the actual tool and evidence capability for each agent; distinguish local HTML extraction from internet browsing and task planning from dynamic execution.
- [ ] Document GitHub Variables/Secrets setup, manual dispatch, allowed main-only ref, output location and failure exit codes.
- [ ] State that a compatible HTTPS endpoint and BYOK secret are required; do not claim a model run until configured and exercised.
- [ ] Run the complete CI suite, dependency audit, catalogue check and verify the PR remains based on `main`.

## Completion Gates

- All catalog entries resolve to executable model-driven AgentDefinitions or explicitly documented non-agent utilities are removed from the agent catalog.
- Each active agent has a unique domain tool capability, a minimum evidence gate and passing end-to-end mock-provider tests.
- A GitHub-hosted Actions run can call a configured HTTPS-compatible endpoint without a local laptop gateway.
- No provider credentials reach untrusted pull-request workflows or repository contents.
- CI, formatting, catalogue validation, tests and dependency audit pass on the same final commit.
