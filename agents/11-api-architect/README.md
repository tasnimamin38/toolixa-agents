# API Architect

**Purpose:** Analyse a local OpenAPI 3.x JSON contract and map its endpoints, parameters, request bodies, response codes and named schemas into an implementation plan.

## What it can do

- Inspect OpenAPI 3.x JSON files.
- Inventory operations and their request/response metadata.
- Identify component schema names and API version information.
- Compare a contract with local source and recommend integration boundaries.
- Produce endpoint mappings, client/server responsibilities, validation needs and compatibility risks.

## What it cannot do

It does not call remote endpoints, authenticate with an API, generate or edit application files, deploy services or claim integration success. YAML OpenAPI files are not supported by this initial tool.

## Run

```powershell
python -m pip install -e "./core[runtime]"
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
python agents/11-api-architect/main.py "Design a typed Python client for the payment API" --workspace C:\path\to\api-project --grant workspace.read
```

## Limits

The deterministic inspector supports OpenAPI 3.x JSON only. Human review is required before using generated integration recommendations.
