# Advanced Specialist Agents and Workflows

**Release:** Experimental alpha on the feature/python-local-ai-gateway branch.

The six advanced specialists share one Python tool-calling runtime. They register real read-only tools, validate model arguments against JSON schemas, require the request's workspace.read grant and return structured evidence. Provider calls go through your local Toolixa Gateway.

## Prerequisites

1. Start the Local AI Gateway from this branch and add a provider in its dashboard.
2. Test the provider and select a model that supports OpenAI Chat Completions-compatible function/tool calling.
3. Create a Toolixa Gateway API key in the dashboard.
4. Keep the API key in the local process environment; never save a real key in Git, agent manifests or source files.

Install both optional extras:

~~~powershell
python -m pip install -e "./core[gateway,runtime]"
~~~

Set the connection in the current PowerShell session:

~~~powershell
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
~~~

Use the exact model ID displayed by the Gateway. The model must support tool calling. No upstream provider key is passed to the agent; the Gateway looks it up in its encrypted local store.

## Six advanced specialists

| Agent | Real tools | Main output |
|---|---|---|
| Software Engineer | file inventory, file reader, search, Python AST, Git diff | codebase map, implementation plan, risks and proposed patch text |
| Code Reviewer | Git diff, file reader, search, Python AST | prioritized findings with file/line evidence |
| Test Engineer | file inventory, file reader, search, Python AST | pytest strategy, missing cases, fixtures and expected assertions |
| Data Analyst | file inventory, file reader, CSV profiler | descriptive statistics and data-quality findings |
| API Architect | file inventory, file reader, OpenAPI 3.x JSON inspector | endpoint/schema inventory and integration architecture |
| Research Analyst | file inventory, file reader, local-document search | evidence-based brief with local file and line citations |

## Engineering Workflow Orchestrator

The thirteenth agent runs the three engineering specialists in one fixed workflow:

1. Software Engineer — project inventory and implementation analysis.
2. Code Reviewer — independent review of the workspace and Engineer's claims.
3. Test Engineer — evidence-based pytest and regression test plan.

Run it from the repository root:

~~~powershell
python agents/13-engineering-workflow/main.py "Review the payments service and propose the safest reliability improvement" --workspace C:\projects\payments --grant workspace.read
~~~

All stages use the same local Gateway client and model. The original task is passed to the Engineer; the Reviewer receives the Engineer's bounded answer as untrusted context; the Test Engineer receives both prior answers as untrusted context. Each stage must call at least one registered read-only tool. The coordinator enforces one shared step/tool-call/wall-clock budget and stops on the first stage failure, permission requirement, missing evidence or budget exhaustion.

The workflow returns one JSON AgentResult with ordered stage summaries, the final test plan, token usage and diagnostics. Exit status is 0 for all-stage success, 2 for failure/budget exhaustion and 3 for explicit permission approval.

## Specialist PowerShell examples

~~~powershell
python agents/07-software-engineer/main.py "Map the architecture and propose a safe refactor of the payment service" --workspace C:\projects\payments --grant workspace.read
python agents/08-code-reviewer/main.py "Review the current changes for security and correctness" --workspace C:\projects\payments --grant workspace.read
python agents/09-test-engineer/main.py "Design regression tests for the authentication module" --workspace C:\projects\payments --grant workspace.read
python agents/10-data-analyst/main.py "Analyse revenue quality and missing data" --workspace C:\datasets --grant workspace.read
python agents/11-api-architect/main.py "Design a typed Python client for the payment API" --workspace C:\projects\api --grant workspace.read
python agents/12-research-analyst/main.py "Summarise authentication decisions and open risks" --workspace C:\projects\payments --grant workspace.read
~~~

Replace example directories with directories you own and intend to inspect.

## Shared specialist CLI options

~~~text
--workspace PATH           Required local workspace root
--grant workspace.read     Explicit read access; without this, tools are denied
--max-steps N              Maximum model/tool loop steps (default 12)
--max-tool-calls N         Maximum tool invocations (default 12)
--max-wall-seconds N       Total wall-clock budget (default 90 seconds)
~~~

For the engineering workflow, these three limits are shared by all stages (defaults: 25 steps, 20 tool calls, 120 seconds). Its original task is capped at 12,000 characters and prior-stage text at 10,000 characters each.

## Tool and safety boundaries

- Workspace tools list, read and search only files under the selected root. Hidden folders, credential-bearing files, symlinks, parent traversal and oversized files are blocked or skipped. Common credential patterns are redacted in excerpts.
- Python inspector parses source into an AST; it never imports, runs or evaluates inspected code.
- Git diff invokes one fixed read-only Git diff command with shell=False, disabled external diff/textconv, a five-second timeout and capped output. It does not execute repository scripts.
- CSV profiler reads a bounded sample of up to 10,000 rows, computes aggregates and avoids returning raw rows. For columns named like passwords, tokens, API keys, SSNs, CVVs or card numbers, it omits distinct counts, category samples and numeric statistics entirely.
- OpenAPI inspector supports OpenAPI 3.x JSON only; YAML and remote URL fetching are not supported.
- Research search searches local Markdown, RST, text and AsciiDoc documents only; it does not browse the public internet.
- Runtime model tool calls are sequential, JSON-schema validated, request-grant checked and bounded by step/tool-call/wall-clock budgets.
- The engineering workflow preserves the fixed three-agent sequence. It does not dynamically spawn agents or expose extra tools.

## What is not enabled

No specialist or workflow stage can write source files, apply patches, run shell commands, execute tests, install packages, make arbitrary HTTP requests, automate a browser or invoke MCP tools. The Software Engineer may propose a diff as text, but it does not apply that diff. Test Engineer proposes tests but does not run them.

The existing DisabledExecutor remains deny-by-default. Read-only Git inspection is a fixed internal operation, not a general-purpose shell tool.

## Troubleshooting

**Missing TOOLIXA_API_KEY:** create a Gateway API key in the local dashboard and set the environment variable again.

**Model not found:** copy the exact namespaced ID from the Gateway's model list into TOOLIXA_MODEL.

**Tool calls unsupported:** choose a model and upstream that support function/tool calling. A chat-only model cannot invoke the specialists' deterministic tools.

**Permission denied:** rerun with --grant workspace.read and verify that --workspace points to the intended directory.

**Provider request failed:** check that the local Gateway is running, the upstream provider connection passes its dashboard test, and the selected model is enabled.

## Status

The specialists and the fixed three-stage workflow are model-plus-tool experimental alpha, not a production autonomous coding environment. Before enabling dynamic delegation or write/execute capabilities, Toolixa needs a separately reviewed agent graph policy, isolated executor, patch approval flow, test runner allowlist, audit trail and adversarial security testing.
