from __future__ import annotations

import pytest

from toolixa_core.runtime.tool_calls import ToolArgumentError, validate_tool_arguments


def test_tool_schema_rejects_missing_required_argument():
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
        "additionalProperties": False,
    }

    with pytest.raises(ToolArgumentError, match="required"):
        validate_tool_arguments(schema, {})


def test_tool_schema_rejects_wrong_types_and_unknown_arguments():
    schema = {
        "type": "object",
        "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 5}},
        "required": ["limit"],
        "additionalProperties": False,
    }

    with pytest.raises(ToolArgumentError, match="integer"):
        validate_tool_arguments(schema, {"limit": True})
    with pytest.raises(ToolArgumentError, match="additional"):
        validate_tool_arguments(schema, {"limit": 3, "command": "whoami"})


def test_tool_schema_validates_nested_objects_and_arrays():
    schema = {
        "type": "object",
        "properties": {
            "paths": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
            "options": {
                "type": "object",
                "properties": {"recursive": {"type": "boolean"}},
                "required": ["recursive"],
                "additionalProperties": False,
            },
        },
        "required": ["paths", "options"],
        "additionalProperties": False,
    }

    validate_tool_arguments(schema, {"paths": ["src", "tests"], "options": {"recursive": True}})
    with pytest.raises(ToolArgumentError, match=r"paths\[1\] must be of type string"):
        validate_tool_arguments(schema, {"paths": ["src", 3], "options": {"recursive": True}})
