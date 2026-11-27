# Task Orchestrator

A deterministic planning foundation. It validates a supplied task graph and returns a topological order. It does not start sub-agents or execute tasks.

## Run

~~~powershell
python main.py --input tasks.json
~~~

Input shape:

~~~json
{
  "tasks": [
    {"id": "design", "depends_on": []},
    {"id": "build", "depends_on": ["design"]},
    {"id": "test", "depends_on": ["build"]}
  ]
}
~~~

The output contains a valid dependency order. Duplicate IDs, missing dependencies, self-dependencies, cycles, and more than 100 tasks are rejected.

## Safety

This agent is a planner only. Multi-agent routing, delegated permission grants, retry policies, and execution are not enabled in this starter.
