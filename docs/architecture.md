# Toolixa Architecture

## System boundary

Toolixa has three distinct surfaces:

1. The public static Agent Directory at https://toolixa-agents.vercel.app.
2. The local Python AI Gateway installed and run by the developer.
3. The Python core SDK, bounded starter agents and model-driven specialist runtime.

The static website does not execute Python agents and is not the Gateway backend. The Gateway and new specialist runtime currently live on the Draft feature branch; the default main branch contains the initial six-agent foundation and static site.

## Local AI flow

~~~text
PowerShell
  -> local Python environment
  -> python -m toolixa_core.gateway
  -> browser dashboard on 127.0.0.1:20128
       -> local dashboard login
       -> configure provider endpoint + provider API key
       -> encrypted local SQLite vault
       -> model discovery and playground
       -> create Toolixa Gateway API key
  -> advanced agent CLI
       -> TOOLIXA_GATEWAY_URL
       -> TOOLIXA_API_KEY (Toolixa key only)
       -> TOOLIXA_MODEL (namespaced model ID)
  -> Gateway /v1/chat/completions
       -> configured upstream provider
       -> assistant tool calls
  -> ToolAgent
       -> validate tool-call JSON schema
       -> check request-scoped RuntimePolicy
       -> enforce step/tool/time budgets
       -> invoke read-only registered tool
       -> append bounded tool result
       -> final AgentResult
~~~

The Gateway accepts trusted upstream endpoints implementing the OpenAI Chat Completions-compatible routes used by the integration. The new GatewayChatClient uses the local Gateway; specialist agents do not receive upstream provider credentials.

## Shared runtime

- contracts defines AgentRequest, AgentResult, ExecutionBudget, artifacts and manifests.
- providers/chat.py provides the optional HTTPX Gateway client, local environment configuration and redacted provider errors.
- runtime/agent.py defines AgentDefinition and ToolAgent; it manages model turns, tool-call IDs, result messages, usage and diagnostics.
- runtime/tool_calls.py validates a bounded JSON Schema subset without a mandatory validation-library dependency.
- tools/base.py declares a tool's name, description, required permissions and JSON parameters schema.
- tools/registry.py publishes tool schemas and validates arguments and permissions before invocation.
- agent_tools contains bounded read-only workspace, Python AST, CSV, OpenAPI JSON, local research and Git diff tools.
- security defines canonical permission names, deny-by-default decisions and ephemeral approvals.
- runtime/executor.py remains disabled by default; there is no general shell or source-write executor.

## Agent portfolio

### Six bounded starter agents

1. Dev Copilot — read-only Python workspace inventory and syntax analysis.
2. Aegis Security — passive local secret-pattern and risky-code checks.
3. Task Orchestrator — deterministic dependency validation and topological order.
4. RAG Chatbot — lexical local document retrieval with source ranges.
5. Content Maestro — editorial briefs and fact-check requirements; it does not browse.
6. Web Scraper — parses supplied local HTML; it does not crawl the internet.

### Six model-driven specialist agents

1. Software Engineer — maps a codebase, reads source, inspects AST and Git diff, and proposes an implementation plan or patch text.
2. Code Reviewer — reviews diffs and source, prioritizing actionable correctness/security findings.
3. Test Engineer — maps modules to tests and proposes pytest fixtures, assertions and regression scenarios.
4. Data Analyst — interprets deterministic local CSV profiling and data-quality statistics.
5. API Architect — inspects OpenAPI 3.x JSON and plans endpoint/schema integrations.
6. Research Analyst — searches local documents and synthesizes evidence with exact file/line references.

Each specialist has a distinct tool set and system instructions. All six require the explicit workspace.read grant. They are model-plus-tool agents, not prompt-only placeholders, but remain experimental and read-only.

## Tool execution and trust

Agent manifests describe capabilities but never grant permissions. Every run supplies explicit grants. Every model-proposed tool call is checked against the agent's registered tools, JSON schema and request-scoped policy. Tool results are bounded before being appended to the conversation.

Prompts, repository contents, retrieved passages, provider output and tool results are untrusted data. They never override runtime policy. Tool calls execute sequentially within the request's step, call and wall-clock budgets.

## Security boundaries

- Local Gateway binds to 127.0.0.1; do not expose it through a tunnel, public reverse proxy or port forward.
- Provider credentials remain encrypted in the Gateway vault. Agents receive only a Toolixa API key via local process environment.
- Workspace tools reject path traversal, symlink escapes, hidden folders and credential-bearing files; source excerpts are redacted.
- Python source inspection uses AST parsing only; it never imports or executes source.
- CSV profiling returns aggregates, not raw dataset rows.
- Git diff uses a fixed read-only command with shell disabled, no external diff/textconv and a short timeout.
- There is no general shell executor, source-write tool, browser automation, remote fetcher or MCP tool bridge in this release.

## Current gaps

- Gateway/provider runtime and twelve-agent catalogue are still on the Draft PR branch, not deployed as a backend to Vercel.
- Native Anthropic/Gemini protocols, arbitrary REST adapters and OAuth are not yet implemented.
- MCP client/server registration and permission-aware tool execution are not implemented.
- Multi-agent delegation, persistent vector memory, browser automation and controlled write/execute sandboxes are not implemented.
- Independent penetration testing, complete CSRF/rate-limit hardening, audit observability and hosted multi-tenant isolation remain outstanding.

## Roadmap

1. Experimental foundation: six bounded agents, Python core interfaces and static directory — on main.
2. Local Gateway and specialist runtime alpha: encrypted BYOK Gateway, model tool-call runtime and six advanced specialists — Draft PR #1.
3. Beta capabilities: native provider protocols, Python MCP SDK integration, persistent source-aware memory, explicit multi-agent delegation and a reviewed approval/patch workflow.
4. Production gate: isolated execution, network egress controls, comprehensive adversarial tests, audit trail, authentication/rate limits and independent security review.
5. Optional hosted SaaS: identity, tenant isolation, remote secret management/KMS, quotas, billing, backups and incident response — only after security review.

## Distribution

The minimal core SDK retains no mandatory third-party dependencies. Install the Gateway with python -m pip install -e "./core[gateway]"; install the model-driven agent runtime with python -m pip install -e "./core[runtime]". A combined local environment can install python -m pip install -e "./core[gateway,runtime]".
