# Development Guide

## Repository layout

- core/ contains Python contracts, policy, runtime, tool registry, read-only tools and the optional local Gateway.
- core/src/toolixa_core/runtime/agent.py contains the shared bounded tool-call loop.
- core/src/toolixa_core/agent_tools/ contains real local evidence tools.
- agents/01-06 contains the initial bounded starter examples.
- agents/07-12 contains six model-driven read-only specialists.
- agents/13 contains the fixed three-stage Engineering Workflow Orchestrator.
- core/src/toolixa_core/workflows/engineering.py coordinates the fixed specialist sequence with one shared budget.
- catalog/agents.json is generated from manifests; do not edit by hand.
- tests/ contains core, gateway, agent, catalogue and static-directory tests.
- docs/ contains architecture, security, install and phase plans.

## Environment setup

~~~powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e "./core[gateway,runtime]"
python -m pip install "pytest>=9.0.3,<10" "ruff>=0.8,<1"
python -m pip install -r agents/06-web-scraper/requirements.txt
~~~

The base core package has no mandatory third-party runtime dependencies. Gateway and model-runtime dependencies are optional extras.

## Run the Gateway and a specialist

Start the local Gateway in one terminal:

~~~powershell
python -m toolixa_core.gateway
~~~

In another PowerShell session, set TOOLIXA_GATEWAY_URL, TOOLIXA_API_KEY and TOOLIXA_MODEL from the local dashboard and run one of agents/07-12 with --workspace PATH --grant workspace.read. To run all three engineering specialists in sequence, use agents/13-engineering-workflow/main.py with the same explicit workspace/grant.

Never commit an actual API key. Use synthetic test fixtures and mock provider responses.

## Runtime contract

A specialist's build_agent() -> AgentDefinition declares its own tools and system prompt. ToolAgent.run(AgentRequest) -> AgentResult performs sequential model/tool turns. A model-issued tool call must:
1. identify a registered tool and unique call ID;
2. contain valid JSON matching that tool's declared parameter schema;
3. pass the request-scoped RuntimePolicy;
4. remain inside the request's step, tool-call and wall-clock budget.

A manifest permission is descriptive only. It never grants access by itself.

## Add a specialist

1. Create agents/NN-name/main.py with a real build_agent() factory.
2. Use existing deterministic tools or add a bounded tool under core/src/toolixa_core/agent_tools/.
3. Give each new tool a JSON parameter schema and explicit permission requirement.
4. Add a distinct system prompt explaining the task and limitations.
5. Add agent.json and a detailed README.
6. Add a fake-provider end-to-end test that proves the real tool is called and its evidence reaches the final answer.
7. Regenerate and validate the catalogue.

Do not list an agent that has no executable behavior, tests or documented scope.

## Local quality checks

~~~powershell
python -m compileall -q core/src agents scripts tests
ruff check core/src agents scripts tests
ruff format --check core/src agents scripts tests
python scripts/build_catalog.py --check
python -m pytest -q
~~~

## Security review checklist

- Does a tool operate only within the selected workspace root?
- Are symlink escapes, path traversal, hidden directories and credentials blocked?
- Does each tool validate its arguments and cap file/output sizes?
- Are prompts, retrieved content and model tool calls treated as untrusted?
- Is every tool invocation checked against the request grant and JSON schema?
- Are wall time, model turns, tool calls and tool results bounded?
- Are secrets omitted from errors, output and logs?
- Is arbitrary process execution still disabled?
- Do tests use fake model responses and deterministic temporary workspaces?

## Current limitations

Specialists are read-only. The Software Engineer can suggest a patch as text but cannot apply it. Test Engineer can propose tests but cannot execute them. Research Analyst searches local files only. Data Analyst supports CSV, API Architect supports OpenAPI 3.x JSON only, and the existing Web Scraper parses supplied local HTML only.

MCP, native Anthropic/Gemini adapters, dynamic/model-selected agent graphs, parallel agent delegation, vector memory, browser automation, source writes, test execution and isolated shell execution are future work. The fixed three-stage engineering workflow is available, but it cannot spawn or reorder agents. Passing tests makes this an experimental alpha, not a production autonomous-agent platform.
