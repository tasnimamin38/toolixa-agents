# Bring Your Own Runtime (BYOR) and Bring Your Own Key (BYOK)

## BYOR

BYOR means the developer chooses where the agent process runs: a local Python virtual environment, a developer-managed container, or an independently operated server. Toolixa does not supply a central execution service.

The Local AI Gateway and the model-driven specialist runtime are Python processes operated by the developer. The current Gateway binds to loopback only. It is not a public service, multi-user control plane, or hardened remote executor.

The advanced specialists use a shared, bounded ToolAgent runtime. The Engineering Workflow Orchestrator runs Software Engineer, Code Reviewer and Test Engineer sequentially through their existing definitions; each registers its own real read-only tools. The coordinator passes bounded prior answers as untrusted context and enforces one overall step, tool-call and wall-clock budget.

This release does not include a production sandbox executor. Arbitrary shell execution, source writes, test execution, browser automation, remote crawling and MCP tool invocation are disabled/not provided. Do not run untrusted code on a workstation that contains personal files, production credentials, or privileged cloud access.

## BYOK

BYOK means provider credentials are supplied by the operator, not embedded in Toolixa. In the local Gateway dashboard, add an upstream provider API key. The server encrypts that key in its local SQLite store and decrypts it only to make an upstream request.

The Gateway stores its local encryption key separately from the SQLite database in the user's application-data directory. Toolixa Gateway client keys are shown once and stored as hashes. The dashboard bootstrap password is printed only on first initialization and stored as a salted scrypt hash. This is local at-rest protection, not a defence against malware or another process running as the same Windows/macOS/Linux user. Keep the local data directory private and never commit it.

Specialist agents do not receive the upstream provider key. They authenticate to the local Gateway using a Toolixa-issued client key supplied through the process environment as TOOLIXA_API_KEY. The model is selected using TOOLIXA_MODEL and the local API base using TOOLIXA_GATEWAY_URL. Never pass a real key in a command-line argument, manifest, source file or report.

Never paste credentials into chat, commit actual keys, print the environment, or serialize credentials into request objects.

## Development installation

1. Create a Python 3.11+ virtual environment.
2. Install the minimal SDK with python -m pip install -e ./core.
3. To run the local dashboard/API, install python -m pip install -e "./core[gateway]".
4. To run the model-driven specialist agents, install python -m pip install -e "./core[runtime]".
5. A combined local installation can use python -m pip install -e "./core[gateway,runtime]".
6. Read the selected agent README and manifest; all advanced specialists and the fixed workflow require an explicit workspace.read grant.
7. Start with a temporary workspace and synthetic data first.
8. Add a provider in the local dashboard only when a model-backed operation needs one.

## Provider compatibility boundary

The local Gateway implements an OpenAI Chat Completions-compatible surface for model listing, non-streaming chat and streaming chat. The ToolAgent runtime uses that local API with function/tool schemas. The selected upstream model must support tool calling for specialist tools to work.

This does not mean every native AI protocol is already supported. Native Anthropic/Gemini protocols, OAuth, arbitrary REST schemas and MCP client/tool execution are separate planned adapters. The current CLI selects one namespaced model per process; per-agent model policy and fallback routing remain future work.

A missing provider configuration must produce an explicit error; no hidden fallback to a different provider is allowed. Do not configure untrusted endpoints: the configured provider receives prompts and conversation content and may have its own retention, privacy and billing terms.

## Python-first implementation

The shared agent contracts, gateway, storage, authentication, HTTP provider adapter, specialist runtime and domain tools are Python. The dashboard uses server-rendered HTML templates and CSS; no Node.js, Go or Rust service is required to run it. Add a lower-level language only when profiling proves Python is the limiting factor and the added build/deployment complexity is justified.
