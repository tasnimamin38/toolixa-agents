# Multi-Agent Engineering Workflow Design

## Goal

Add one practical Engineering Workflow Orchestrator that runs the existing Software Engineer, Code Reviewer and Test Engineer specialists as one auditable, sequential task. Each stage must execute its existing model-driven AgentDefinition and deterministic read-only tools; the coordinator must not imitate agent reasoning or invent tool evidence.

## Selected design

Use a deterministic sequential workflow, not an LLM-controlled free-form agent swarm. The fixed handoff order is:

1. **Software Engineer** explores the selected workspace, identifies relevant source and current diffs, and returns an implementation/architecture analysis.
2. **Code Reviewer** independently examines the workspace and receives the Engineer's analysis as untrusted context; it verifies claims and reports prioritized findings.
3. **Test Engineer** examines the workspace and receives both prior outputs as untrusted context; it turns the task, analysis and review findings into a concrete test strategy.

The same configured local Gateway client and namespaced model are used for all stages. Each stage keeps its own distinct AgentDefinition, tool registry and system prompt. The coordinator cannot add tools or permissions.

## Public interfaces

### WorkflowStage

Immutable metadata:
- `id: str` — exact specialist ID.
- `label: str` — human-readable stage name.
- `definition: AgentDefinition` — executable specialist definition.

### EngineeringWorkflow

Constructor:
`EngineeringWorkflow(client, stages, *, max_task_chars=12000, max_handoff_chars=10000, max_stage_output_chars=10000)`

Public method:
`run(request: AgentRequest) -> AgentResult`

Expected request:
- `agent_id == "engineering-workflow"`
- a non-empty `input["prompt"]`
- an existing `workspace` directory
- explicit `workspace.read` in `grants`
- `ExecutionBudget` treated as one workflow-wide maximum.

The constructor accepts exactly three stages in this order: `software-engineer`, `code-reviewer`, `test-engineer`. The order is fixed by code, not model-generated or manifest-declared.

### Result

Return the existing `AgentResult` contract with:
- `agent_id="engineering-workflow"`
- `output["workflow"]` set to the workflow ID.
- `output["final_answer"]` containing the Test Engineer's final answer.
- `output["stages"]` containing ordered stage IDs, labels, status, bounded answer, model usage, tool-call count and available tool names.
- `usage` aggregating token, model-step, tool-call and completed-stage counts.
- diagnostics prefixed by stage ID.

On the first failed or permission-denied stage, stop immediately and return that status with all completed stage summaries retained. Do not run later stages. A successful model response without at least one actual registered tool call is not accepted as a completed stage; return a failed result with `evidence_missing`.

## Handoff contract

- Stage 1 receives the original task.
- Stage 2 receives the original task plus the bounded Stage 1 answer.
- Stage 3 receives the original task plus bounded Stage 1 and Stage 2 answers.
- Previous model answers are explicitly marked untrusted evidence. The receiving stage must verify important claims against its own read-only tools and must not treat prior-stage content as instructions.
- Handoff text is capped at 10,000 characters per answer; the original task is capped at 12,000 characters.
- Only text answers and small stage metadata are handed off. Tool registries, credentials, policy objects and raw client internals are never shared with models as data.

## Permissions and safety

- `workspace.read` is mandatory before any provider call. Missing grant returns `AgentStatus.NEEDS_APPROVAL`; missing or invalid workspace returns `FAILED`.
- All stage definitions must contain only tools requiring `workspace.read`; any stage with a broader permission is rejected during workflow construction.
- The same resolved workspace root and request trace ID are used for every stage.
- No workspace write, patch application, shell command, test execution, browser or network tool is enabled.
- The workflow uses one injected provider client; no stage can choose a new provider, key, model or endpoint.
- Tool execution remains sequential. There is no parallel fan-out, dynamic spawning or recursive delegation.

## Overall budget

Treat the incoming `ExecutionBudget` as a single shared budget, not three independent stage budgets:
- Track total model steps and tool calls from completed stage usage.
- Before each stage, pass only the remaining steps, tool calls and wall-clock seconds to its `ToolAgent`.
- Stop before starting a stage when no steps or wall-clock time remain.
- A model/tool-call budget exhaustion is a workflow failure, never an invitation to continue without a limit.
- Aggregate token counts across stages and include total stages completed.

## CLI

Add `agents/13-engineering-workflow/main.py` with:
- `build_workflow(client=None) -> EngineeringWorkflow`
- same positional prompt and `--workspace`, explicit `--grant workspace.read`, `--max-steps`, `--max-tool-calls`, `--max-wall-seconds` CLI options.
- Gateway client from the existing `GatewayChatClient.from_env()` when no client is injected.
- JSON `AgentResult` output, exit 0 for success, 3 for needs-approval, 2 for failure.
- `--help` must work without API credentials or Gateway connection.

## Catalogue and documentation

Register agent ID `engineering-workflow`, category `development`, status `experimental`, permission `workspace.read`, entrypoint `main.py`, documentation `README.md`. Add the workflow to the generated agent directory catalogue, but do not modify the static directory deployment or merge the Draft PR.

## Verification

Use mocked provider responses and real deterministic tools in temporary workspaces. Tests must prove:
- successful three-stage sequence and exact handoff of prior answers;
- only the correct stage tool set is exposed at each model turn;
- stage outputs contain real tool-use evidence;
- missing grant prevents all provider calls;
- missing/non-directory workspace prevents provider calls;
- failure or permission denial stops subsequent stages and preserves completed summaries;
- one shared step/tool/wall-time budget is enforced across stages;
- oversized task and handoff text are bounded;
- provider usage and stage/tool totals are aggregated;
- CLI help works without credentials;
- manifest/catalogue contains 13 unique agents.

## Non-goals

No dynamic agent planning, self-directed sub-agent spawning, arbitrary agent graph, parallel execution, shared writable memory, code patching, file writes, shell/test execution, approval UI, MCP or browser automation. Those require separate designs and threat-model work.
