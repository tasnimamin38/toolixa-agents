# Engineering Workflow Orchestrator

**Purpose:** Run three existing Toolixa specialists as one bounded, evidence-backed engineering task.

## Fixed stage order

1. **Software Engineer** explores the selected project and produces an implementation/architecture analysis.
2. **Code Reviewer** independently checks the workspace and reviews the Engineer's claims and risks.
3. **Test Engineer** uses the original task, engineering analysis and review findings to produce a test strategy.

Each stage calls the configured local Gateway model through the shared Toolixa tool-calling runtime and uses only its own registered read-only tools. Every successful stage must invoke at least one real tool. Prior answers are passed as untrusted text, not as instructions.

## Run

Install the Gateway and runtime extras from the repository root:

~~~powershell
python -m pip install -e "./core[gateway,runtime]"
~~~

Set the local Toolixa Gateway connection:

~~~powershell
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
~~~

Run the workflow against a project directory you own:

~~~powershell
python agents/13-engineering-workflow/main.py "Review the payments service and propose the safest reliability improvement" --workspace C:\projects\payments --grant workspace.read
~~~

The CLI returns one structured JSON `AgentResult` containing all three stage summaries, the final Test Engineer answer, aggregate token/step/tool-call usage and any diagnostics.

## Options

~~~text
--workspace PATH           Required existing local project directory
--grant workspace.read     Explicit read-only grant; required before any model call
--max-steps N              Shared maximum model turns across all stages (default 25)
--max-tool-calls N         Shared maximum tool calls across all stages (default 20)
--max-wall-seconds N       Shared overall wall-clock limit in seconds (default 120)
~~~

Exit codes: 0 = all three stages succeeded; 2 = failed/budget exhausted; 3 = explicit permission required.

## Safety and limitations

- Stage order is fixed in code; the model cannot add, reorder or spawn agents.
- All three stages use the same configured Gateway client, model, workspace root and trace ID.
- Each stage receives only its own registered tools and the explicit `workspace.read` grant.
- One overall step/tool-call/wall-clock budget is shared by all stages; it is not reset after handoff.
- If a stage fails, lacks tool evidence, is denied permission or exhausts its budget, the workflow stops and returns completed stage summaries.
- Original task text and each prior-stage answer are bounded; prior answers are treated as untrusted context.
- The workflow can inspect source, read Git diff, search local files and parse Python AST. It does not write files, apply patches, execute code, run tests, use shell commands, browse the internet or invoke MCP tools.
- The Test Engineer proposes test commands and cases; the workflow does not execute them.

This is an experimental, local, read-only multi-agent workflow—not an autonomous coding system or production SaaS feature.
