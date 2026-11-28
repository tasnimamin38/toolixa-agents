# Research Analyst

**Purpose:** Search local project documentation and prepare evidence-backed briefs with exact source locations.

## What it can do

- Search local Markdown, text, reStructuredText and AsciiDoc documents.
- Rank matching passages and return workspace-relative paths and line numbers.
- Synthesize claims from retrieved source passages.
- Compare passages and highlight conflicts, gaps and unanswered questions.

## What it cannot do

This agent does not browse the public internet, open remote URLs, scrape websites or verify current news. It will say when local evidence is missing rather than inventing sources.

## Run

```powershell
python -m pip install -e "./core[runtime]"
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
python agents/12-research-analyst/main.py "Summarise our authentication architecture and open risks" --workspace C:\path\to\repo --grant workspace.read
```

## Limits

Research scope is the selected local workspace only. Citations refer to files and line numbers, not external sources. The model's interpretation should be checked against the cited passages.
