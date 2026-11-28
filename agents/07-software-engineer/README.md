# Software Engineer

**Purpose:** Model-powered engineering analysis for complex codebases. This agent first maps the repository, then reads relevant modules, inspects Python structure and checks the current Git diff before proposing an implementation.

## What it can do

- Build a bounded project file inventory.
- Search source and documentation for symbols or behavior.
- Read selected files with line-numbered evidence.
- Inspect Python imports, functions, classes and syntax without execution.
- Read the uncommitted Git diff.
- Produce a staged implementation plan, proposed changes, tests, risks and review checklist.

## What it cannot do

It does not edit files, run shell commands, execute code, install packages, commit changes or claim that a patch was applied. Proposed patches are returned as text for review.

## Run

Install the shared runtime from the repository root:

```powershell
python -m pip install -e "./core[runtime]"
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
python agents/07-software-engineer/main.py "Design a safe modular refactor for the payment workflow" --workspace C:\path\to\repo --grant workspace.read
```

The API key is read from the process environment; never put a real key in this README, a manifest or source code.

## Limits

The Gateway must already be running locally and have the chosen provider/model configured. All workspace tools are read-only and bounded. This agent is experimental and requires a human to review and apply any proposed changes.
