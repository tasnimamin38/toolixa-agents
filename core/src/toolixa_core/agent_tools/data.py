"""Bounded CSV profiling with standard-library parsing and descriptive statistics."""

from __future__ import annotations

import csv
import io
import math
import statistics
from collections import Counter
from typing import Any

from toolixa_core.agent_tools.workspace import read_workspace_text
from toolixa_core.logging import redact
from toolixa_core.tools.base import ToolCallContext, ToolSpec

_SENSITIVE_COLUMN_PARTS = ("password", "secret", "token", "api_key", "ssn", "cvv", "card_number")


class ProfileCSVTool:
    spec = ToolSpec(
        "data.profile_csv",
        "Profile a local CSV using bounded row sampling. Returns dimensions, missing/duplicate counts, inferred column types and numeric summaries; it does not upload or mutate the file.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 500},
                "max_rows": {"type": "integer", "minimum": 1, "maximum": 10000},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        relative, content = read_workspace_text(context, arguments["path"], max_bytes=2_000_000)
        maximum = arguments.get("max_rows", 5000)
        if not 1 <= maximum <= 10_000:
            raise ValueError("max_rows must be between 1 and 10,000")
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise ValueError("CSV must contain a header row")
        columns = [name.strip() if name else "" for name in reader.fieldnames]
        if any(not name for name in columns) or len(set(columns)) != len(columns):
            raise ValueError("CSV column names must be non-empty and unique")

        values: dict[str, list[str]] = {name: [] for name in columns}
        missing = Counter()
        duplicates = Counter()
        rows_profiled = 0
        truncated = False
        for row in reader:
            if rows_profiled >= maximum:
                truncated = True
                break
            normalized = tuple((row.get(name) or "").strip() for name in columns)
            duplicates[normalized] += 1
            rows_profiled += 1
            for name, value in zip(columns, normalized, strict=True):
                if not value:
                    missing[name] += 1
                elif len(values[name]) < 10_000:
                    values[name].append(value)

        summaries: dict[str, dict[str, Any]] = {}
        for name in columns:
            samples = values[name]
            numeric: list[float] = []
            numeric_count = 0
            for value in samples:
                try:
                    number = float(value)
                except ValueError:
                    continue
                if math.isfinite(number):
                    numeric.append(number)
                    numeric_count += 1
            sensitive = any(part in name.casefold() for part in _SENSITIVE_COLUMN_PARTS)
            is_numeric = bool(samples) and numeric_count == len(samples)
            item: dict[str, Any] = {
                "type": "numeric"
                if is_numeric
                else ("empty" if not samples else "categorical_or_mixed"),
                "missing": missing[name],
                "non_empty_profiled": len(samples),
                "sensitive_column": sensitive,
            }
            if not sensitive:
                item["unique_values"] = len(set(samples))
                if is_numeric and numeric:
                    ordered = sorted(numeric)
                    item.update(
                        {
                            "minimum": min(numeric),
                            "maximum": max(numeric),
                            "mean": round(statistics.fmean(numeric), 6),
                            "median": statistics.median(ordered),
                        }
                    )
                elif samples:
                    item["top_values"] = [
                        {"value": redact(value)[:100], "count": count}
                        for value, count in Counter(samples).most_common(5)
                    ]
            summaries[name] = item

        return {
            "path": relative.as_posix(),
            "columns": summaries,
            "rows_profiled": rows_profiled,
            "duplicate_rows": sum(count - 1 for count in duplicates.values() if count > 1),
            "truncated": truncated,
            "raw_rows_returned": 0,
        }
