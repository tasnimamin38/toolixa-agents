# Advanced Agent Runtime and Specialist Agents Design

## Purpose

Upgrade Toolixa from a static catalogue plus bounded starter scripts into a model-driven, tool-using local agent system. Add a shared execution runtime and six advanced specialist agents that perform materially useful, inspectable tasks rather than acting as prompt-only placeholders.

## Product outcome

A developer configures one Toolixa Local AI Gateway model and a gateway-issued API key in local environment variables. They can then run a specialist agent from PowerShell. Each agent sends a task to the selected model, exposes only its registered tools, and executes only those tool calls that pass JSON-schema checks, explicit request grants, workspace boundaries, and request budgets.

The first specialist release is deliberately read-only. Software changes, test execution, shell commands, browser automation, remote crawling, and MCP tool invocation are not silently enabled.

## Architecture

### Shared runtime

- `GatewayChatClient` calls the configured local Toolixa Gateway's OpenAI Chat Completions-compatible `/chat/completions` API using a Toolixa-issued bearer key.
- `ToolAgent` manages system/user messages, model calls, tool-call parsing, tool results, final answers, diagnostics, and bounded turn counts.
- `ToolRegistry` exposes only tools registered by one agent and enforces the existing `RuntimePolicy` before execution.
- `ToolSpec` contains a JSON Schema object used both for model-facing tool declarations and runtime argument validation.
- The existing `ExecutionBudget` governs steps, tool calls, and wall time. Runtime adds fixed upper bounds for prompt, provider response and tool-result sizes.
- A run returns the existing `AgentResult` contract, including status, answer, token usage and redacted diagnostics.

### Local integration

The runtime reads:
- `TOOLIXA_GATEWAY_URL` — optional; defaults to `http://127.0.0.1:20128/v1`.
- `TOOLIXA_API_KEY` — required Toolixa gateway client key. It is read only from the local process environment.
- `TOOLIXA_MODEL` — required namespaced model ID listed by the gateway, for example `openrouter/qwen-model`.

No upstream provider key is copied into the agent process. Provider secrets remain in the Gateway's local encrypted vault.

### Specialist agents

The six new agents are:
1. **Software Engineer** — builds a bounded source inventory, reads relevant files, checks Python AST/syntax and reviews the current Git diff; returns a structured implementation plan and proposed changes. It does not modify the workspace.
2. **Code Reviewer** — reviews Git changes and source files for correctness, security, maintainability and missing tests; returns prioritized findings with file/line evidence. It does not rewrite files.
3. **Test Engineer** — maps source modules to existing tests, compiles Python sources without executing them, and proposes focused test cases and commands. It does not run arbitrary tests.
4. **Data Analyst** — profiles a local CSV file, reports shape, columns, missing values, duplicate rows and descriptive numeric summaries, then asks the model to interpret the measured evidence.
5. **API Architect** — inspects a local OpenAPI JSON document, resolves operation metadata and schemas, and produces implementation/integration recommendations. YAML support is not included in this slice.
6. **Research Analyst** — searches local Markdown/text documentation, returns exact source passages and line ranges, and synthesizes claims only from retrieved evidence. It does not claim to browse the internet.

All six use the shared model-and-tool runtime and require explicit `workspace.read` grants. Tools are read-only, workspace-bound, and have bounded file count, file size, match count, row count and output size.

## Security and failure behavior

- A manifest capability is descriptive only and does not grant runtime permissions.
- Missing `workspace.read` grants prevent the tool from running.
- Unknown tools, malformed JSON, invalid arguments, invalid tool-call IDs and provider errors are recorded as bounded diagnostics; none trigger arbitrary execution.
- Tool call loops stop at the request step/tool/wall-clock budget.
- Files must resolve inside the selected workspace. Symlink escapes, parent traversal, hidden/system folders and oversized files are rejected or skipped.
- No `shell=True`, dynamic `eval`, `exec`, code execution, writes, network fetches or implicit agent-to-agent delegation are introduced.
- API keys are never logged, emitted in diagnostics, placed in manifests or written to source files.
- If the model does not return a final text answer within the budget, the run returns a failed result with diagnostics rather than claiming success.

## Verification

Use mock provider responses only. Automated tests cover:
- successful answer without tools;
- a complete tool-call round trip with exact tool result ID;
- missing permissions and workspace path escapes;
- invalid/malformed JSON tool arguments and unknown tool names;
- repeated calls, max-step/max-tool-call/time limits;
- oversized tool outputs and provider errors;
- each specialist's actual local deterministic analysis tool;
- catalog discovery and entrypoint smoke behavior.

Full regression commands: `python -m compileall -q core/src agents scripts tests`, `ruff check core/src agents scripts tests`, `ruff format --check core/src agents scripts tests`, `python scripts/build_catalog.py --check`, and `python -m pytest -q`.

## Release status

This delivers an advanced **experimental** local runtime and specialist-agent alpha. It is not an autonomous coding system with write/execute permissions, not an MCP client, not an internet research crawler, and not a production SaaS service. Those need separate approval boundaries and threat-model work.
