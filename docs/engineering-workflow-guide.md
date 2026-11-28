# Engineering Workflow Orchestrator

**Agent ID:** `engineering-workflow`

**Status:** Experimental alpha on `feature/python-local-ai-gateway`.

This workflow coordinates three existing specialists using their actual model-driven `ToolAgent` definitions and registered read-only tools. It is a fixed, auditable pipeline—not an LLM-created agent swarm.

## What happens

1. **Software Engineer** inventories and inspects the project, reads relevant source and Git diff, and produces architecture/implementation analysis.
2. **Code Reviewer** independently inspects the same workspace and checks the Engineer's claims, returning prioritized findings with file evidence.
3. **Test Engineer** examines the task and prior outputs and turns them into a focused test strategy, pytest scenarios, fixtures and assertions.

Each stage uses its own tools and system prompt. Every stage must execute at least one real registered tool before its result is accepted. If a stage fails, is denied, exhausts the shared budget or returns no tool evidence, later stages do not run. Completed stage summaries are retained in the final JSON result.

## Run

Install both optional extras and start the local Gateway as described in the installation guide:

~~~powershell
python -m pip install -e "./core[gateway,runtime]"
~~~

Set the local Gateway connection and choose a tool-calling model:

~~~powershell
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
~~~

Run it from the repository root against a project you own:

~~~powershell
python agents/13-engineering-workflow/main.py "Review the payments service and propose the safest reliability improvement" --workspace C:\projects\payments --grant workspace.read
~~~

The CLI prints one structured `AgentResult` containing the ordered stage outputs, final Test Engineer answer, aggregate token/model-step/tool-call usage and diagnostics.

## Shared budget options

~~~text
--workspace PATH           Required existing local project directory
--grant workspace.read     Explicit read grant required before any provider call
--max-steps N              Maximum model turns across all three stages (default 25)
--max-tool-calls N         Maximum tool calls across all three stages (default 20)
--max-wall-seconds N       One overall wall-clock limit (default 120 seconds)
~~~

The budget is not reset between agents. Before a stage starts, the coordinator passes only the remaining step, tool-call and wall-time capacity to that stage. Every evidence stage needs at least one tool call and a subsequent model turn to interpret it.

Exit codes: 0 = all three stages succeeded; 2 = failure or budget exhaustion; 3 = permission approval required.

## Handoff and trust

The first stage receives the original task. The Code Reviewer receives the task plus the bounded Engineer answer. The Test Engineer receives the task plus the bounded Engineer and Reviewer answers.

Prior-stage answers are explicitly marked as untrusted claims, not instructions. Each following specialist is instructed to verify relevant claims against its own workspace tools. The same configured Gateway client/model, resolved workspace root and request trace ID are used across all stages. No credentials, tool registries or permission objects are serialized into handoff prompts.

The original task is capped at 12,000 characters; prior-stage answers are capped at 10,000 characters each, and final stage output is bounded.

## Safety boundaries

- Each stage retains its own tools; the coordinator does not union tool permissions.
- All three definitions are checked to require `workspace.read` only.
- No model can change stage order, spawn arbitrary agents, add tools or select a different provider.
- No source writes, patch application, shell commands, test execution, browser/network tools, internet research or MCP calls are available.
- The Test Engineer designs tests and commands; it does not execute them.
- The workflow does not make code changes. Human review and a separately designed, approved execution sandbox are required for that future capability.

This is a fixed read-only workflow alpha. It is not autonomous coding, unrestricted multi-agent delegation or a production hosted service.
