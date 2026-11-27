# Code Reviewer

**Purpose:** Review current working-tree changes and relevant source for correctness, security, reliability, maintainability and test gaps.

## What it can do

- Read the current uncommitted Git diff.
- Inspect relevant files and search for related call sites.
- Parse Python source and summarize imports, functions, classes and syntax.
- Return prioritized findings (Critical, High, Medium, Low), evidence locations, impact, and a suggested fix.
- Separate confirmed defects from questions and uncertain risks.

## What it cannot do

It does not modify code, execute tests, run commands, push commits or claim an issue has been fixed. It only sees uncommitted changes visible to `git diff`; staged/committed history may require a later Git-history tool.

## Run

```powershell
python -m pip install -e "./core[runtime]"
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
python agents/08-code-reviewer/main.py "Review the current changes for security and correctness" --workspace C:\path\to\repo --grant workspace.read
```

## Limits

The review is model-assisted, not a formal proof or substitute for tests, SAST/DAST or an independent security audit. Findings should be verified before changing code.
