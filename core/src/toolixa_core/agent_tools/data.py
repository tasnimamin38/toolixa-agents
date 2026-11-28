"""Bounded CSV profiling and privacy-aware dataset comparison."""

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

_SENSITIVE_COLUMN_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "ssn",
    "cvv",
    "card_number",
)


def _is_sensitive(name: str) -> bool:
    return any(part in name.casefold() for part in _SENSITIVE_COLUMN_PARTS)


def _parse_csv(
    context: ToolCallContext, path: str, maximum: int
) -> tuple[str, list[str], list[dict[str, str]], bool]:
    relative, content = read_workspace_text(context, path, max_bytes=2_000_000)
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError(f"{path} must contain a CSV header row")
    columns = [name.strip() if name else "" for name in reader.fieldnames]
    if any(not name for name in columns) or len(set(columns)) != len(columns):
        raise ValueError(f"{path} must contain unique, non-empty column names")
    rows: list[dict[str, str]] = []
    truncated = False
    for row in reader:
        if len(rows) >= maximum:
            truncated = True
            break
        rows.append({name: (row.get(name) or "").strip() for name in columns})
    return relative.as_posix(), columns, rows, truncated


def _numeric_values(rows: list[dict[str, str]], column: str) -> list[float] | None:
    values = [row[column] for row in rows if row.get(column, "").strip()]
    if not values:
        return None
    numbers: list[float] = []
    for value in values:
        try:
            number = float(value)
        except ValueError:
            return None
        if not math.isfinite(number):
            return None
        numbers.append(number)
    return numbers


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
        maximum = arguments.get("max_rows", 5000)
        if not 1 <= maximum <= 10000:
            raise ValueError("max_rows must be between 1 and 10,000")
        relative, columns, rows, truncated = _parse_csv(context, arguments["path"], maximum)
        missing: Counter[str] = Counter()
        duplicates: Counter[tuple[str, ...]] = Counter()
        for row in rows:
            normalized = tuple(row[name] for name in columns)
            duplicates[normalized] += 1
            for name in columns:
                if not row[name]:
                    missing[name] += 1

        summaries: dict[str, dict[str, Any]] = {}
        for name in columns:
            values = [row[name] for row in rows if row[name]]
            sensitive = _is_sensitive(name)
            numeric = _numeric_values(rows, name)
            item: dict[str, Any] = {
                "type": "numeric" if numeric is not None else ("empty" if not values else "categorical_or_mixed"),
                "missing": missing[name],
                "non_empty_profiled": len(values),
                "sensitive_column": sensitive,
            }
            if not sensitive:
                item["unique_values"] = len(set(values))
                if numeric:
                    item.update(
                        {
                            "minimum": min(numeric),
                            "maximum": max(numeric),
                            "mean": round(statistics.fmean(numeric), 6),
                            "median": statistics.median(numeric),
                        }
                    )
                elif values:
                    item["top_values"] = [
                        {"value": redact(value)[:100], "count": count}
                        for value, count in Counter(values).most_common(5)
                    ]
            summaries[name] = item

        return {
            "path": relative,
            "columns": summaries,
            "rows_profiled": len(rows),
            "duplicate_rows": sum(count - 1 for count in duplicates.values() if count > 1),
            "truncated": truncated,
            "raw_rows_returned": 0,
        }


class CompareCSVDatasetsTool:
    spec = ToolSpec(
        "data.compare_csv_datasets",
        "Compare two bounded local CSV snapshots by schema, inferred type, missingness, key overlap, duplicates and numeric mean drift. Never returns raw rows or values from sensitive columns.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "before_path": {"type": "string", "minLength": 1, "maxLength": 500},
                "after_path": {"type": "string", "minLength": 1, "maxLength": 500},
                "key_columns": {
                    "type": "array",
                    "maxItems": 5,
                    "items": {"type": "string", "minLength": 1, "maxLength": 120},
                },
                "max_rows": {"type": "integer", "minimum": 1, "maximum": 10000},
            },
            "required": ["before_path", "after_path"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        maximum = arguments.get("max_rows", 5000)
        if not 1 <= maximum <= 10000:
            raise ValueError("max_rows must be between 1 and 10,000")
        before_path, before_columns, before_rows, before_truncated = _parse_csv(
            context, arguments["before_path"], maximum
        )
        after_path, after_columns, after_rows, after_truncated = _parse_csv(
            context, arguments["after_path"], maximum
        )
        before_set, after_set = set(before_columns), set(after_columns)
        common = sorted(before_set & after_set)
        added = sorted(after_set - before_set)
        removed = sorted(before_set - after_set)
        key_columns = arguments.get("key_columns", [])
        if (
            not isinstance(key_columns, list)
            or len(key_columns) > 5
            or len(set(key_columns)) != len(key_columns)
            or any(not isinstance(name, str) or not name.strip() for name in key_columns)
        ):
            raise ValueError("key_columns must be a list of up to five unique column names")
        if any(name not in before_set or name not in after_set for name in key_columns):
            raise ValueError("every key column must exist in both CSV datasets")

        column_quality: dict[str, dict[str, Any]] = {}
        type_changes: list[dict[str, str]] = []
        numeric_drift: dict[str, dict[str, Any]] = {}
        sensitive_columns: dict[str, dict[str, bool]] = {}
        for name in common:
            before_values = [row[name] for row in before_rows if row[name]]
            after_values = [row[name] for row in after_rows if row[name]]
            before_numbers = _numeric_values(before_rows, name)
            after_numbers = _numeric_values(after_rows, name)
            before_type = (
                "numeric" if before_numbers is not None else ("empty" if not before_values else "categorical_or_mixed")
            )
            after_type = (
                "numeric" if after_numbers is not None else ("empty" if not after_values else "categorical_or_mixed")
            )
            if before_type != after_type:
                type_changes.append({"column": name, "before": before_type, "after": after_type})
            sensitive = _is_sensitive(name)
            column_quality[name] = {
                "before_missing": len(before_rows) - len(before_values),
                "after_missing": len(after_rows) - len(after_values),
                "missing_delta": (len(after_rows) - len(after_values)) - (len(before_rows) - len(before_values)),
                "before_type": before_type,
                "after_type": after_type,
                "sensitive_column": sensitive,
            }
            if sensitive:
                sensitive_columns[name] = {"statistics_suppressed": True}
                continue
            if before_numbers is not None and after_numbers is not None:
                before_mean = statistics.fmean(before_numbers)
                after_mean = statistics.fmean(after_numbers)
                absolute_change = after_mean - before_mean
                relative_change = (
                    round((absolute_change / abs(before_mean)) * 100, 6)
                    if before_mean != 0
                    else None
                )
                numeric_drift[name] = {
                    "before_mean": round(before_mean, 6),
                    "after_mean": round(after_mean, 6),
                    "absolute_change": round(absolute_change, 6),
                    "relative_change_percent": relative_change,
                    "before_non_empty": len(before_numbers),
                    "after_non_empty": len(after_numbers),
                }

        key_comparison: dict[str, Any] | None = None
        if key_columns:
            def key_set(rows: list[dict[str, str]]) -> tuple[set[tuple[str, ...]], int]:
                counts: Counter[tuple[str, ...]] = Counter()
                for row in rows:
                    key = tuple(row[name] for name in key_columns)
                    if all(key):
                        counts[key] += 1
                return set(counts), sum(count - 1 for count in counts.values() if count > 1)

            before_keys, before_duplicates = key_set(before_rows)
            after_keys, after_duplicates = key_set(after_rows)
            key_comparison = {
                "key_columns": key_columns,
                "matched_key_rows": len(before_keys & after_keys),
                "before_only_key_rows": len(before_keys - after_keys),
                "after_only_key_rows": len(after_keys - before_keys),
                "before_duplicate_key_rows": before_duplicates,
                "after_duplicate_key_rows": after_duplicates,
                "before_missing_key_rows": sum(
                    1 for row in before_rows if any(not row[name] for name in key_columns)
                ),
                "after_missing_key_rows": sum(
                    1 for row in after_rows if any(not row[name] for name in key_columns)
                ),
                "key_values_returned": False,
            }

        return {
            "before_path": before_path,
            "after_path": after_path,
            "before_rows_profiled": len(before_rows),
            "after_rows_profiled": len(after_rows),
            "before_truncated": before_truncated,
            "after_truncated": after_truncated,
            "added_columns": added,
            "removed_columns": removed,
            "type_changes": type_changes,
            "column_quality": column_quality,
            "numeric_drift": numeric_drift,
            "sensitive_columns": sensitive_columns,
            "key_comparison": key_comparison,
            "matched_key_rows": key_comparison["matched_key_rows"] if key_comparison else None,
            "before_only_key_rows": key_comparison["before_only_key_rows"] if key_comparison else None,
            "after_only_key_rows": key_comparison["after_only_key_rows"] if key_comparison else None,
            "raw_rows_returned": 0,
        }
