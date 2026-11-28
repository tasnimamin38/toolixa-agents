# Toolixa Security Model

## Threat model

Toolixa agents and Gateway may process untrusted source files, HTML, retrieved documents, prompts, provider responses, task descriptions, API credentials and URLs. Risks include prompt injection, accidental disclosure, path traversal, SSRF, excessive execution, secret leakage, replay/CSRF, and unsafe agent delegation.

## Defaults

- No permission is granted merely because an agent manifest declares it.
- No arbitrary shell/process execution is available through the default executor.
- Active security scanning is disabled unless a future explicit target grant is separately designed and tested.
- Workspace access is limited to the root explicitly supplied for the request.
- Network access requires an explicit permission and exact host allowlist; no general-purpose network fetch tool is included in the specialist alpha.
- Provider credentials must not appear in source, manifests, catalogues, logs, traces or reports.
- The first Web Scraper parses local HTML only; it does not make HTTP requests.
- The local Gateway binds to 127.0.0.1, does not enable CORS, and restricts accepted Host headers to loopback/test hosts. Do not tunnel or expose it publicly.

## Permission names

workspace.read, workspace.write, network.http, process.execute, browser.automate, security.scan.passive, security.scan.active, provider.invoke, memory.read, and memory.write are canonical permission names.

A grant is supplied per AgentRequest. The advanced specialists currently request only workspace.read, and the CLI requires the operator to pass --grant workspace.read. Manifest declarations never grant runtime access.

## Model-driven tool-call runtime

- Each agent registers only its own tool objects and JSON parameter schemas.
- Model-proposed tool calls are checked for valid JSON, known function name, unique call ID, declared schema and required permission before invocation.
- Tools run sequentially. The existing ExecutionBudget enforces step count, tool-call count and total wall-clock time; each provider request receives only the remaining time budget.
- Tool result JSON and diagnostics are bounded and passed through secret redaction.
- Unknown tools, malformed arguments, denied permissions, tool failures and provider errors produce structured diagnostics; they do not fall back to arbitrary code execution.
- Tool descriptions and system prompts are guidance, not security controls. The actual boundary is the registered tool set, argument validator, request policy and bounded tool implementation.
- Failed model requests preserve counts of tools already completed, so aggregate workflow usage does not erase partial work.

## Evidence-backed expert-agent runtime

The six model-driven specialists are read-only:

- Software Engineer: local inventory, source reads, search, Python AST and fixed Git diff; returns plans and patch text but cannot apply changes.
- Code Reviewer: examines diffs and source; cannot change code or execute tests.
- Test Engineer: designs test cases and commands; does not run tests or write files.
- Data Analyst: returns CSV aggregates; does not upload or mutate raw data.
- API Architect: inspects local OpenAPI 3.x JSON; does not call endpoints.
- Research Analyst: searches local documents; does not browse the public internet.

The existing six starter agents retain their documented boundaries. The thirteenth agent, Engineering Workflow Orchestrator, runs Software Engineer -> Code Reviewer -> Test Engineer in a fixed sequence. It passes prior text outputs as untrusted context, shares one global step/tool/time budget and stops on failure or missing evidence. It accepts only stages whose tools require workspace.read; it cannot add tools, change provider/model, reorder stages, spawn arbitrary agents or elevate permissions. All thirteen are experimental.

## Domain analysis tools

- Python Security AST inspection parses source without executing it and emits rule IDs, severity and source locations, never source lines or secret values.
- Delivery planning validates the task DAG and calculates earliest/latest schedule, critical path, slack and owner workload; it does not launch tasks.
- OpenAPI comparison detects selected backwards-incompatible changes in local OpenAPI 3.x JSON. It does not dereference `$ref`, parse YAML or call remote APIs.
- Script-timeline analysis measures supplied hook spacing, timeline gaps and final CTA coverage; it does not predict actual view retention.
- Static HTML crawling is restricted to a supplied workspace snapshot and makes zero network requests.
- Python module graph analysis parses local source into AST and detects local import cycles without importing or executing project code.

## Workspace data protections

Workspace tools resolve each requested file under the selected root, reject POSIX/Windows absolute paths and parent traversal, reject symlink paths and symlink escapes, exclude hidden/credential-bearing paths and cap file count/size/output. Common credential patterns are redacted in file excerpts and tool results.

Python inspection parses source using ast; it does not import or execute inspected code. CSV profiling samples a bounded number of rows and returns aggregates rather than raw rows. Git diff uses a fixed read-only Git invocation with shell=False, disabled external diff/textconv, a five-second timeout and capped output.

## Local Gateway credentials

- The dashboard bootstrap password is displayed once, then stored as a salted scrypt hash.
- Upstream provider API keys are encrypted in SQLite using Fernet. The vault key lives separately in the user's application-data directory.
- Toolixa API keys are displayed once and stored as hashes.
- The Gateway API key used by agents must be supplied through the local process environment as TOOLIXA_API_KEY. Never pass it as a command-line argument or place it in a manifest/source file.
- TOOLIXA_GATEWAY_URL defaults to loopback http://127.0.0.1:20128/v1; TOOLIXA_MODEL selects an exact namespaced model ID exposed by the Gateway.

Encryption at rest protects a database-only copy from exposing provider keys. It does not protect against malware or another process running as the same user and able to read both database and vault key.

## Execution isolation

DisabledExecutor remains the built-in executor and always refuses process execution. The specialist agents and fixed workflow do not receive a shell, source-write, test-runner or browser tool. The fixed read-only Git diff tool is narrowly bounded and is not an arbitrary command interface.

A future coding agent that applies patches or runs tests must use a reviewed isolation boundary, explicit per-action approval, workspace snapshots/rollback, command allowlists, resource/network limits and an auditable action log. A container by itself is not a complete security boundary.

## Prompt injection and evidence

Repository contents, CSV headers, documents, code comments, API descriptions, model responses, previous-stage handoffs and tool results are untrusted data. They may contain instruction-like text. The runtime does not treat them as policy; only code-defined registered tools and user-granted permissions determine what can be executed.

Research Analyst cites local source paths and line numbers. It must not claim to have searched the web or verified live facts.

## Outstanding security work

The feature branch's latest GitHub-hosted verification passed 112 tests, compilation, Ruff lint/format and catalogue validation. This does not replace an independent penetration test. Remaining work includes comprehensive CSRF/session review, login and API rate limiting, provider response-size limits, tamper-evident audit, secret-rotation/recovery, DNS/IP pinning or enforced egress controls for any future remote fetching, sandboxed write/execute tools, MCP adversarial testing, hosted identity and tenant isolation.

This is an experimental, single-user, loopback-only Gateway and read-only workflow alpha. Do not deploy it as a public service or trust model outputs without human review.
