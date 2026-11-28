# Multi-Agent Engineering Workflow Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Implementation commit `3d4453e` is pushed on `feature/python-local-ai-gateway`; 90 local tests pass and GitHub CI plus Dependency Security both passed for that commit. Independent security review remains pending.

**Goal:** Add a real, bounded engineering workflow that coordinates the existing Software Engineer, Code Reviewer and Test Engineer in one sequential, evidence-backed task.

**Architecture:** A deterministic coordinator invokes the existing three `AgentDefinition` objects through the shared `ToolAgent` runtime, using one local Gateway client and a fixed handoff order. The coordinator shares the original task, prior bounded text answers, workspace root, trace ID and one overall execution budget; it never spawns tools or grants permissions itself.

**Tech Stack:** Python 3.11+, existing `AgentRequest`/`AgentResult` contracts, `ToolAgent`, local Gateway HTTPX client, pytest, Ruff and GitHub Actions.

## Global Constraints

- The workflow runs exactly three stages in this order: Software Engineer, Code Reviewer, Test Engineer.
- Each stage must execute at least one registered read-only tool before its output can be accepted.
- `workspace.read` is mandatory; the workspace path must exist and resolve to a directory.
- Each agent keeps its own tool registry; no cross-agent permission union is created.
- One configured model/client and the same request trace ID are shared across all three stages.
- The original task is capped at 12,000 characters; each prior-stage answer handed forward is capped at 10,000 characters.
- `ExecutionBudget` is enforced across the entire workflow, not reset to the original limits per stage.
- A failed, cancelled, or needs-approval stage stops the workflow; later stages do not run.
- Workflow stage tools remain read-only. No file writes, patch application, shell execution, test execution, browser, network, MCP or dynamic agent spawning.
- Tests use mocked provider responses and temporary workspaces; no real inference call or provider credentials are needed.
- The new workflow remains experimental and is a thirteenth catalogue entry on the existing feature branch only.

**Spec:** `docs/specs/2026-11-28-multi-agent-engineering-workflow-design.md`

---

### Task 1: Add the workflow contract and enforce a three-stage sequence

**Files:**
- Create: `core/src/toolixa_core/workflows/__init__.py`
- Create: `core/src/toolixa_core/workflows/engineering.py`
- Test: `tests/workflows/test_engineering_workflow.py`

**Interfaces:**
- `WorkflowStage(id: str, label: str, definition: AgentDefinition)`
- `EngineeringWorkflow(client, stages, *, max_task_chars=12000, max_handoff_chars=10000, max_stage_output_chars=10000)`
- `EngineeringWorkflow.run(request: AgentRequest) -> AgentResult`

- [x] Add failing tests for constructor stage order/count, missing `workspace.read`, missing workspace, successful three-stage model/tool sequence, exact prior-answer handoff and evidence requirement.
- [x] Run `python -m pytest tests/workflows/test_engineering_workflow.py -q`; missing `toolixa_core.workflows` caused the expected collection failure before implementation.
- [x] Implement request validation, resolved workspace handling, shared trace ID, stage-scoped requests, bounded handoffs and sequential `ToolAgent` execution.
- [x] Require at least one actual tool call per successful stage, preserve ordered summaries and stop on failure/approval requirement.
- [x] Verify focused tests using registered read-only test tools; all 11 workflow tests passed.
- [x] Run Ruff on the workflow package and focused tests.

### Task 2: Enforce one workflow-wide execution budget and result aggregation

**Files:**
- Modify: `core/src/toolixa_core/workflows/engineering.py`
- Modify: `core/src/toolixa_core/runtime/agent.py`
- Test: `tests/workflows/test_engineering_workflow.py`
- Test: `tests/core/test_agent_runtime.py`

- [x] Add tests for shared remaining steps/tool calls/wall time and aggregate usage across completed stages.
- [x] Verify the global budget tests fail before the implementation exists and pass after implementation.
- [x] Pass only remaining global limits to each stage and stop before starting when fewer than two steps, no tool-call budget or no wall time remains.
- [x] Preserve partial tool-call counts in failed `AgentResult` objects when a provider fails or budget expires after a tool has already run.
- [x] Verify max-step, max-tool-call, wall-clock, output truncation and usage aggregation behavior.
- [x] Run the focused runtime/workflow tests.

### Task 3: Add the Engineering Workflow CLI and thirteenth manifest

**Files:**
- Create: `agents/13-engineering-workflow/main.py`
- Create: `agents/13-engineering-workflow/agent.json`
- Create: `agents/13-engineering-workflow/README.md`
- Create: `agents/13-engineering-workflow/requirements.txt`
- Create: `core/src/toolixa_core/workflow_runtime_cli.py`
- Modify: `catalog/agents.json`
- Modify: `tests/test_catalog.py`
- Test: `tests/agents/test_engineering_workflow_cli.py`

**Interfaces:**
- `build_workflow(client=None) -> EngineeringWorkflow`
- `run_workflow_cli(workflow_factory, *, description, argv=None) -> int`
- CLI options: positional task, `--workspace`, repeatable explicit `--grant workspace.read`, `--max-steps`, `--max-tool-calls`, `--max-wall-seconds`.

- [x] Add CLI tests for `--help` without credentials, missing Gateway API key, explicit workspace/grant behavior and JSON/exit status through an injected fake workflow.
- [x] Verify the entrypoint help command succeeds without a provider key and the real CLI returns a clear error rather than falling back when `TOOLIXA_API_KEY` is missing.
- [x] Load the existing three specialist definitions through the bounded local loader and inject one `GatewayChatClient` into the workflow.
- [x] Implement JSON result output and exit codes (0 success, 3 needs approval, 2 failure).
- [x] Add a thirteenth manifest and README; regenerate the catalogue and validate 13 unique manifests.
- [x] Use exact uppercase `README.md` naming in the new agent directory for Linux case-sensitive filesystems.
- [x] Run CLI, catalogue and workflow tests.

### Task 4: Documentation, integration and release checks

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/security-model.md`
- Modify: `docs/advanced-agents-guide.md`
- Modify: `docs/installation.md`
- Modify: `docs/development.md`
- Modify: `docs/byor-guide.md`
- Create: `docs/engineering-workflow-guide.md`
- Create: this implementation plan and the associated design spec.

- [x] Document the fixed three-stage sequence, evidence requirement, handoffs, budget aggregation and read-only boundaries.
- [x] Update the portfolio to thirteen entries and add the PowerShell CLI command.
- [x] Regenerate the catalogue and validate all 13 manifests.
- [x] Run local compile, Ruff, format, catalogue and full regression checks.

## Local verification evidence

**Windows / Python 3.11.9**

- Ruff check — all checks passed.
- Ruff format — **84 Python files already formatted**.
- `compileall` — passed for core, agents, scripts and tests.
- Catalogue — valid and up to date; **13 unique agent manifests**.
- Full pytest — **90 passed**.
- `git diff --check` — passed.
- Tests use mocked model responses and temporary workspaces; no real API key or paid model call is used.

## Pending release checks

- [x] Re-run the full local verification after the last CLI test addition; all 90 tests passed.
- [x] Commit and push implementation to `feature/python-local-ai-gateway` as `3d4453ec66c7334eb4d40cf7d5ecb310dd8b434c`; PR #1 remains Draft.
- [x] Verify GitHub Actions CI (run `46151186105`) and Dependency Security (run `46151186111`) on that implementation commit; both passed.
- [ ] Complete independent code/security review before changing this PR out of Draft or merging to main.

## Release gate

- The three existing specialists execute in the fixed order through their real registered tools.
- Each stage's prompt includes only the task and bounded prior text outputs, not credentials or permission objects.
- A stage without tool evidence is never marked completed.
- Missing workspace permission prevents all provider calls.
- No later stage executes after failure, approval requirement or exhausted shared budget.
- Total step/tool/time and token usage is inspectable in the final AgentResult.
- The catalogue contains thirteen unique agents with valid entrypoints/docs.
- CI and Dependency Security pass on the final feature-branch commit.
- This is an experimental workflow alpha, not a production autonomous coding system.
