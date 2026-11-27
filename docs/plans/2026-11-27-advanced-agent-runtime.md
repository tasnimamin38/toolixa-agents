# Advanced Agent Runtime and Specialist Agents Implementation Plan

**Status:** Local implementation and regression complete on `feature/python-local-ai-gateway`; GitHub PR checks and independent security review are pending.

**Goal:** Add a bounded, model-driven Python tool-calling runtime and six functional specialist agents to Toolixa Agents.

**Architecture:** A shared runtime calls the local Toolixa Gateway's OpenAI-compatible API, validates model-issued tool calls against registered JSON schemas and existing request-scoped policy, and returns the existing `AgentResult` contract. Six specialist agents provide read-only domain tools, so model reasoning is paired with real local evidence without granting shell, write, browser, or remote-network execution.

**Tech Stack:** Python 3.11+, standard library, optional HTTPX runtime extra, FastAPI Gateway, pytest, Ruff and GitHub Actions.

**Spec:** `docs/specs/2026-11-27-advanced-agent-runtime-design.md`

## Release constraints

- Core SDK has no mandatory third-party runtime dependencies.
- Provider credentials remain in the local Gateway vault; agents only receive a Toolixa client key from process environment.
- Each run requires a model and explicit request-scoped grants.
- Specialist tools are read-only in this alpha.
- Arbitrary shell, `eval`, `exec`, file writes, test execution, browser automation, remote fetching and MCP invocation remain unavailable.
- Tool execution is sequential and bounded by step/tool/wall-clock budgets.
- Provider interactions in tests are mocked; no real paid model call or real provider credential is required.
- All six new agents remain experimental pending security review and later integration phases.

## Completed implementation tasks

### Task 1: Gateway chat client and model tool-call contracts

- [x] Add `GatewayChatClient` for the local Toolixa Gateway `/chat/completions` API.
- [x] Read URL, Toolixa API key and namespaced model from `TOOLIXA_GATEWAY_URL`, `TOOLIXA_API_KEY` and `TOOLIXA_MODEL`.
- [x] Validate loopback URL policy, bearer authentication, model payload, tool schema payload and JSON responses.
- [x] Disable redirects and environment proxy inheritance; redact bearer key from provider errors.
- [x] Keep HTTPX under optional `[runtime]` dependencies; base core dependencies remain empty.
- [x] Add mock-transport tests for defaults, invalid URLs, auth, error redaction and tool schemas.

### Task 2: Bounded tool-calling Agent Runtime

- [x] Add `AgentDefinition` and `ToolAgent` returning the existing `AgentResult`.
- [x] Extend `ToolSpec` with JSON parameter schemas and publish OpenAI-compatible function declarations.
- [x] Validate object/string/integer/number/boolean/array schemas, required fields, nested properties/items and additional-property policy.
- [x] Validate model tool-call IDs, JSON arguments, registered tool names and result objects.
- [x] Enforce request-scoped `RuntimePolicy` before invoking tools.
- [x] Enforce max steps, tool calls and total wall time; each provider request receives only the remaining wall-time budget.
- [x] Bound prompts, tool arguments, tool outputs and diagnostics; redact secrets from tool results and errors.
- [x] Add tests for text-only final answers, successful tool round trips, denied permissions, malformed JSON, unknown tools, budgets, truncation, provider errors and remaining-time propagation.

### Task 3: Read-only evidence tools

- [x] Add bounded workspace file inventory, file reading and text search.
- [x] Reject path traversal and symlink paths/escapes; exclude hidden folders and credential-bearing paths; cap file count, size and output.
- [x] Add Python AST/source inspection without importing or executing source.
- [x] Add fixed read-only Git diff inspection with `shell=False`, no external diff/textconv, a five-second timeout and capped output.
- [x] Add local CSV profiling for up to 10,000 rows with missingness, duplicates and descriptive statistics.
- [x] Suppress all category/value/unique/numeric statistics for sensitive-named CSV columns (password, secret, token, API key, SSN, CVV, card number).
- [x] Add OpenAPI 3.x JSON inspection (no remote endpoint calls; YAML is not supported).
- [x] Add local Markdown/RST/text/AsciiDoc retrieval with exact file and line references; no internet browsing.
- [x] Add deterministic tests for fixtures, source locations, sensitive columns and workspace safety.

### Task 4: Six model-powered specialist agents

- [x] Add Software Engineer with workspace inventory/read/search, Python AST and Git diff tools.
- [x] Add Code Reviewer with Git diff/source/search/AST tools.
- [x] Add Test Engineer with project/test inventory, source/search and Python syntax/AST tools.
- [x] Add Data Analyst with deterministic CSV profile tool.
- [x] Add API Architect with OpenAPI JSON inspector.
- [x] Add Research Analyst with local-document search and evidence citations.
- [x] Give each agent a distinct prompt, `build_agent()`, real registered tool set, CLI, manifest, README and explicit `workspace.read` grant.
- [x] Add fake-provider end-to-end tests proving each specialist calls its real tool and returns the final model answer.
- [x] Add CLI `--help` smoke tests without requiring a provider key.
- [x] Update catalog generation and catalogue tests for twelve unique manifest entries (six original + six advanced).

### Task 5: Documentation, catalogue and CI

- [x] Update README with twelve-agent portfolio, advanced specialist capabilities, accurate branch status and safety boundaries.
- [x] Update architecture, security, installation, development, BYOR/BYOK and Gateway guidance.
- [x] Add a dedicated Advanced Specialist Agents guide with model setup, PowerShell commands, tool capabilities and limitations.
- [x] Add an advanced runtime design specification and this implementation plan.
- [x] Update CI and dependency security workflows to install `[gateway,runtime]`.
- [x] Regenerate catalogue and verify twelve manifests and valid entrypoints/docs.
- [x] Use exact uppercase README.md paths in all six specialist manifests and folders; Linux GitHub runner validation exposed the case-sensitive path mismatch that Windows does not expose.
- [x] Run full local Windows/Python 3.11 checks: Ruff check/format, compileall, catalogue validation and pytest.

## Local verification evidence

**Windows / Python 3.11.9**

- Ruff: all checks passed.
- Format: 77 Python files already formatted.
- Compile: all core, agents, scripts and tests compiled.
- Catalogue: valid and up to date; twelve unique agents.
- Tests: **72 passed** after sensitive-column privacy regression coverage was added.
- No real provider key, paid model call or external model inference was used by the test suite.

## Pending release checks

- [ ] Commit and push the completed branch changes.
- [ ] Verify fresh GitHub Actions CI and Dependency Security workflow runs for the final pushed commit.
- [ ] Complete independent code/security review before changing this PR out of Draft or merging to main.

## Release gate

- No new agent may be listed unless it has a working `build_agent()`, at least one real deterministic tool, a manifest, CLI and behavior tests.
- Tool calls are validated, sequential, permission checked and budget limited.
- All twelve agents are discoverable in the generated directory catalogue.
- Existing six starter-agent behavior remains intact.
- Runtime code does not silently enable write, shell, browser, network or MCP access.
- Passing local or GitHub checks establishes an experimental alpha, not production readiness.
