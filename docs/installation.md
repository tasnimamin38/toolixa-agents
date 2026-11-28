# Installation Guide

## Requirements

- Python 3.11 or newer.
- Git.
- A local Toolixa Gateway for model-powered specialist agents.
- A provider/model configured in the Gateway that supports OpenAI Chat Completions-compatible function/tool calling.

The public Vercel directory is static and does not run Python agents. The Gateway is a separate local Python process.

## Clone the current feature branch

The Gateway and model-driven specialist runtime are currently in Draft PR #1, not on the default main branch.

~~~powershell
git clone --branch feature/python-local-ai-gateway https://github.com/tasnimamin38/toolixa-agents.git
cd toolixa-agents

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
~~~

## Install the Gateway and specialist runtime

~~~powershell
python -m pip install -e "./core[gateway,runtime]"
~~~

This installs the optional FastAPI Gateway, encryption and HTTPX client while keeping the core package's mandatory dependencies empty.

## Start the local Gateway

~~~powershell
python -m toolixa_core.gateway
~~~

The terminal prints a one-time dashboard password. Open http://127.0.0.1:20128 and add a provider endpoint and upstream API key in the dashboard. Test the connection, choose a model that supports tool calling, and create a Toolixa Gateway API key.

The server listens on loopback only. Stop it with Ctrl+C. Do not tunnel, port-forward or reverse-proxy this experimental dashboard/API to the public internet.

## Configure specialist agents in PowerShell

~~~powershell
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
~~~

Use the exact namespaced model ID shown by the Gateway. The Toolixa key is the local Gateway client key, not the upstream provider key. Never put a real key in source code, manifests, README files or command-line arguments.

## Run an advanced specialist

Each specialist requires an explicit workspace and read permission.

~~~powershell
python agents/07-software-engineer/main.py "Map the architecture and propose a safe refactor" --workspace C:\path\to\repo --grant workspace.read

python agents/08-code-reviewer/main.py "Review current changes for security and correctness" --workspace C:\path\to\repo --grant workspace.read

python agents/09-test-engineer/main.py "Design regression tests for authentication" --workspace C:\path\to\repo --grant workspace.read

python agents/10-data-analyst/main.py "Analyse revenue and missing data" --workspace C:\path\to\data --grant workspace.read

python agents/11-api-architect/main.py "Design a typed client for this API" --workspace C:\path\to\api-project --grant workspace.read

python agents/12-research-analyst/main.py "Summarise the documented architecture and risks" --workspace C:\path\to\repo --grant workspace.read
~~~

Optional controls: --max-steps, --max-tool-calls, --max-wall-seconds. The CLI prints a structured JSON AgentResult and returns exit code 0 on success, 2 on failure and 3 when the run needs an explicit permission grant.

## Run the fixed Engineering Workflow

The thirteenth agent runs the existing Software Engineer, Code Reviewer and Test Engineer in order, with one shared execution budget:

~~~powershell
python agents/13-engineering-workflow/main.py "Review the payments service and propose the safest reliability improvement" --workspace C:\path\to\repo --grant workspace.read
~~~

The workflow requires a real read-only tool call at every stage. It passes prior answers as untrusted context and stops on the first failure, missing evidence or exhausted step/tool/time budget. It does not write code or execute tests. See [Engineering Workflow Guide](engineering-workflow-guide.md).

## Existing starter agents

The six initial agents remain under agents/01-* through agents/06-*. Read each agent's README and install only its declared direct dependency. They do not automatically require the model gateway.

## Verify the repository

~~~powershell
python -m compileall -q core/src agents scripts tests
ruff check core/src agents scripts tests
ruff format --check core/src agents scripts tests
python scripts/build_catalog.py --check
python -m pytest -q
~~~

CI uses mocked model responses; no real provider key or paid inference request is needed for the test suite.

## Current limits

The six model-driven specialists and fixed Engineering Workflow are experimental and read-only. The workflow runs Software Engineer -> Code Reviewer -> Test Engineer in a fixed sequence, requires workspace.read, and shares one global step/tool/time budget. No dynamic agent spawning, code writes, patch application, test execution, arbitrary shell, public internet browsing or MCP tool invocation is enabled. Native provider protocols, MCP, memory, controlled patch application and isolated execution are future phases.
