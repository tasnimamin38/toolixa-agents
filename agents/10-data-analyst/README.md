# Data Analyst

**Purpose:** Inspect a local CSV dataset and explain its measured shape, quality and descriptive statistics.

## What it can do

- Profile up to 10,000 CSV rows per request.
- Report columns, inferred types, missing values and distinct-value counts.
- Detect duplicate rows in the profiled sample.
- Calculate numeric minimum, maximum, mean and median.
- Explain trends, data limitations and next analytical steps using measured results.

## What it cannot do

It does not alter the CSV, upload raw rows, write reports to disk, connect to databases or claim causal conclusions from descriptive statistics. Sensitive-named columns are not returned as category samples.

## Run

```powershell
python -m pip install -e "./core[runtime]"
$env:TOOLIXA_GATEWAY_URL = "http://127.0.0.1:20128/v1"
$env:TOOLIXA_API_KEY = "YOUR_TOOLIXA_GATEWAY_KEY"
$env:TOOLIXA_MODEL = "provider-id/model-id"
python agents/10-data-analyst/main.py "Analyse revenue quality and missing data" --workspace C:\path\to\data --grant workspace.read
```

## Limits

CSV profiling is bounded and standard-library based. Large files are sampled up to the requested row limit; outputs state when profiling was truncated. Verify any business decision with domain context.
