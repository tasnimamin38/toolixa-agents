# Test Engineer

**Purpose:** Turn complex feature requirements and source code into a concrete test strategy with focused pytest cases and regression coverage.

## What it can do

- Map source modules to existing test files.
- Inspect Python AST and syntax without executing source.
- Search for branches, error handling and permission checks.
- Identify missing boundary, regression and adversarial tests.
- Propose fixtures, exact assertions, and PowerShell commands to run later.

## What it cannot do

It does not run tests, launch subprocesses, install packages or write test files. It produces a reviewable test plan and example test code only.

## Run

```powershell
python -m pip install -e "./core[runtime]"
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
python agents/09-test-engineer/main.py "Design regression tests for the authentication module" --workspace C:\path\to\repo --grant workspace.read
```

## Limits

It analyses local workspace evidence only. Proposed tests must be executed and reviewed by a developer; no claim of a passing test run is made.
