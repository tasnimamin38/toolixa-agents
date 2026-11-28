"""Validate editorial briefs and their source-reference coverage."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from toolixa_core.tools.base import ToolCallContext, ToolSpec


class ValidateEditorialBriefTool:
    spec = ToolSpec(
        "content.validate_editorial_brief",
        "Check editorial structure and whether factual claims have plausible HTTPS references. Does not fetch sources or certify truth.",
        (),
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 200},
                "audience": {"type": "string", "minLength": 1, "maxLength": 200},
                "content_format": {"type": "string", "minLength": 1, "maxLength": 100},
                "sections": {
                    "type": "array",
                    "maxItems": 50,
                    "items": {"type": "string", "minLength": 1, "maxLength": 300},
                },
                "claims": {
                    "type": "array",
                    "maxItems": 100,
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {"type": "string", "minLength": 1, "maxLength": 1000},
                            "source_urls": {
                                "type": "array",
                                "maxItems": 10,
                                "items": {"type": "string", "minLength": 1, "maxLength": 2048},
                            },
                        },
                        "required": ["claim", "source_urls"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["title", "audience", "content_format", "sections", "claims"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        del context
        unsupported = []
        malformed = []
        for index, claim in enumerate(arguments["claims"], 1):
            if not claim["source_urls"]:
                unsupported.append(index)
            for url in claim["source_urls"]:
                parsed = urlsplit(url)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                ):
                    malformed.append(
                        {"claim_index": index, "reason": "source must be an absolute HTTPS URL"}
                    )
        return {
            "valid_structure": bool(arguments["sections"]) and not unsupported and not malformed,
            "title_present": bool(arguments["title"].strip()),
            "audience_present": bool(arguments["audience"].strip()),
            "sections_count": len(arguments["sections"]),
            "claims_count": len(arguments["claims"]),
            "claims_without_source": unsupported,
            "invalid_source_references": malformed,
            "source_fetch_performed": False,
            "fact_accuracy_verified": False,
        }


class AnalyzeScriptTimelineTool:
    spec = ToolSpec(
        "content.analyze_script_timeline",
        "Evaluate a video script's timestamped segments for timeline continuity, coverage, re-hook spacing and a final call-to-action. This measures the supplied beat map; it does not predict audience retention.",
        (),
        {
            "type": "object",
            "properties": {
                "expected_duration_seconds": {"type": "integer", "minimum": 1, "maximum": 7200},
                "target_hook_interval_seconds": {"type": "integer", "minimum": 5, "maximum": 600},
                "segments": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 200,
                    "items": {
                        "type": "object",
                        "properties": {
                            "start_seconds": {"type": "number", "minimum": 0, "maximum": 7200},
                            "end_seconds": {"type": "number", "minimum": 0, "maximum": 7200},
                            "label": {"type": "string", "minLength": 1, "maxLength": 160},
                            "hook": {"type": "boolean"},
                            "cta": {"type": "boolean"},
                        },
                        "required": ["start_seconds", "end_seconds", "label", "hook"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["expected_duration_seconds", "target_hook_interval_seconds", "segments"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        del context
        expected = arguments["expected_duration_seconds"]
        target = arguments["target_hook_interval_seconds"]
        segments = sorted(arguments["segments"], key=lambda item: item["start_seconds"])
        errors: list[str] = []
        previous_end = 0.0
        hook_times: list[float] = []
        for index, item in enumerate(segments):
            start = item["start_seconds"]
            end = item["end_seconds"]
            if end <= start:
                errors.append(f"segment {index + 1} has a non-positive duration")
            if start < previous_end:
                errors.append(f"segment {index + 1} overlaps the previous segment")
            elif start > previous_end:
                errors.append(f"timeline gap before segment {index + 1}")
            if end > expected:
                errors.append(f"segment {index + 1} extends beyond expected duration")
            previous_end = max(previous_end, end)
            if item["hook"]:
                hook_times.append(float(start))
        if previous_end < expected:
            errors.append("timeline does not cover the expected ending")
        hook_gaps = [
            {
                "from_seconds": left,
                "to_seconds": right,
                "gap_seconds": right - left,
                "exceeds_target": right - left > target,
            }
            for left, right in zip(hook_times, hook_times[1:], strict=False)
        ]
        longest_gap = max((item["gap_seconds"] for item in hook_gaps), default=0.0)
        missing_final_cta = not bool(segments[-1].get("cta", False))
        if longest_gap > target * 1.5 or missing_final_cta:
            risk = "high"
        elif longest_gap > target or errors:
            risk = "moderate"
        else:
            risk = "low"
        return {
            "timeline_valid": not errors,
            "timeline_errors": errors,
            "hook_count": len(hook_times),
            "hook_times_seconds": hook_times,
            "hook_gaps": hook_gaps,
            "longest_hook_gap_seconds": longest_gap,
            "target_hook_interval_seconds": target,
            "missing_final_cta": missing_final_cta,
            "retention_risk": risk,
            "audience_retention_predicted": False,
        }
