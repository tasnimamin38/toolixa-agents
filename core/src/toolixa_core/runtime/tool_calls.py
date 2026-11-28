"""Strict, dependency-free validation for model-proposed tool arguments."""

from __future__ import annotations

from typing import Any


class ToolArgumentError(ValueError):
    """Raised when a model-proposed tool call does not match its declared schema."""


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    raise ToolArgumentError(f"unsupported schema type: {expected}")


def _validate_value(schema: dict[str, Any], value: Any, path: str) -> None:
    expected = schema.get("type")
    if not isinstance(expected, str) or not _matches_type(value, expected):
        raise ToolArgumentError(f"{path} must be of type {expected or 'declared'}")

    if "enum" in schema and value not in schema["enum"]:
        raise ToolArgumentError(f"{path} is not an allowed value")

    if expected == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            raise ToolArgumentError(f"{path} has an invalid object schema")
        missing = [name for name in required if name not in value]
        if missing:
            raise ToolArgumentError(f"{path} is missing required field(s): {', '.join(missing)}")
        if schema.get("additionalProperties", False) is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise ToolArgumentError(f"{path} contains additional field(s): {', '.join(extra)}")
        for name, item in value.items():
            if name in properties:
                child_schema = properties[name]
                if not isinstance(child_schema, dict):
                    raise ToolArgumentError(f"{path}.{name} has an invalid schema")
                _validate_value(child_schema, item, f"{path}.{name}")

    if expected == "array":
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ToolArgumentError(f"{path} has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ToolArgumentError(f"{path} has too many items")
        item_schema = schema.get("items")
        if item_schema is not None:
            if not isinstance(item_schema, dict):
                raise ToolArgumentError(f"{path} has an invalid items schema")
            for index, item in enumerate(value):
                _validate_value(item_schema, item, f"{path}[{index}]")

    if expected == "string":
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ToolArgumentError(f"{path} is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ToolArgumentError(f"{path} is too long")

    if expected in {"integer", "number"}:
        if "minimum" in schema and value < schema["minimum"]:
            raise ToolArgumentError(f"{path} is below the minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ToolArgumentError(f"{path} is above the maximum")


def validate_tool_arguments(schema: dict[str, Any], arguments: Any) -> dict[str, Any]:
    """Validate an object against the bounded JSON Schema subset used by ToolSpec."""
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ToolArgumentError("tool parameters schema must describe an object")
    if not isinstance(arguments, dict):
        raise ToolArgumentError("tool arguments must be a JSON object")
    _validate_value(schema, arguments, "arguments")
    return arguments
