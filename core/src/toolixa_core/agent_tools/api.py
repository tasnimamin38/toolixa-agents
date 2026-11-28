"""Read-only OpenAPI 3.x JSON contract inspection."""

from __future__ import annotations

import json
from typing import Any

from toolixa_core.agent_tools.workspace import read_workspace_text
from toolixa_core.tools.base import ToolCallContext, ToolSpec


class InspectOpenAPITool:
    spec = ToolSpec(
        "api.inspect_openapi_json",
        "Inspect a local OpenAPI 3.x JSON file and summarize API operations, parameters, request bodies, response codes and component schemas. YAML is not supported.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {"path": {"type": "string", "minLength": 1, "maxLength": 500}},
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        relative, content = read_workspace_text(context, arguments["path"], max_bytes=2_000_000)
        try:
            document = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAPI document is not valid JSON") from exc
        if not isinstance(document, dict):
            raise ValueError("OpenAPI document root must be an object")
        version = document.get("openapi")
        if not isinstance(version, str) or not version.startswith("3."):
            raise ValueError("only OpenAPI 3.x JSON documents are supported")
        info = document.get("info")
        if not isinstance(info, dict):
            raise ValueError("OpenAPI document must include an info object")
        paths = document.get("paths")
        if not isinstance(paths, dict):
            raise ValueError("OpenAPI document must include a paths object")

        operations: list[dict[str, Any]] = []
        methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
        for path, path_item in sorted(paths.items()):
            if not isinstance(path_item, dict):
                continue
            for method, operation in sorted(path_item.items()):
                if method.lower() not in methods or not isinstance(operation, dict):
                    continue
                parameters = operation.get("parameters", [])
                responses = operation.get("responses", {})
                body = operation.get("requestBody")
                operations.append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "operation_id": operation.get("operationId", ""),
                        "summary": operation.get("summary", ""),
                        "parameter_count": len(parameters) if isinstance(parameters, list) else 0,
                        "request_body_required": bool(body.get("required"))
                        if isinstance(body, dict)
                        else False,
                        "response_codes": sorted(responses) if isinstance(responses, dict) else [],
                    }
                )
                if len(operations) >= 200:
                    break
            if len(operations) >= 200:
                break

        components = document.get("components", {})
        schemas = components.get("schemas", {}) if isinstance(components, dict) else {}
        return {
            "path": relative.as_posix(),
            "openapi_version": version,
            "title": info.get("title", ""),
            "api_version": info.get("version", ""),
            "servers": [
                server.get("url", "")
                for server in document.get("servers", [])
                if isinstance(server, dict) and isinstance(server.get("url"), str)
            ][:10],
            "operations": operations,
            "operation_count": len(operations),
            "schemas": sorted(schemas)[:300] if isinstance(schemas, dict) else [],
            "truncated": len(operations) >= 200,
        }


class CompareOpenAPIContractsTool:
    spec = ToolSpec(
        "api.compare_openapi_contracts",
        "Compare two local OpenAPI 3.x JSON contracts and identify backwards-incompatible operation, parameter, response and component-schema changes. Reference resolution and YAML are not supported.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "before_path": {"type": "string", "minLength": 1, "maxLength": 500},
                "after_path": {"type": "string", "minLength": 1, "maxLength": 500},
                "max_changes": {"type": "integer", "minimum": 1, "maximum": 300},
            },
            "required": ["before_path", "after_path"],
            "additionalProperties": False,
        },
    )

    @staticmethod
    def _document(path: str, context: ToolCallContext) -> tuple[str, dict[str, Any]]:
        relative, content = read_workspace_text(context, path, max_bytes=2_000_000)
        try:
            document = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"OpenAPI document {path} is not valid JSON") from exc
        if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith("3."):
            raise ValueError(f"OpenAPI document {path} must be an OpenAPI 3.x JSON object")
        if not isinstance(document.get("paths"), dict):
            raise ValueError(f"OpenAPI document {path} must include paths")
        return relative.as_posix(), document

    @staticmethod
    def _operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        methods = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
        operations: dict[tuple[str, str], dict[str, Any]] = {}
        for path, item in document["paths"].items():
            if not isinstance(item, dict):
                continue
            for method, operation in item.items():
                if method.lower() in methods and isinstance(operation, dict):
                    operations[(method.upper(), path)] = operation
        return operations

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        before_path, before = self._document(arguments["before_path"], context)
        after_path, after = self._document(arguments["after_path"], context)
        maximum = arguments.get("max_changes", 200)
        if not 1 <= maximum <= 300:
            raise ValueError("max_changes must be between 1 and 300")
        old_ops = self._operations(before)
        new_ops = self._operations(after)
        changes: list[dict[str, Any]] = []

        def add(rule_id: str, location: str, message: str) -> None:
            if len(changes) < maximum:
                changes.append(
                    {
                        "rule_id": rule_id,
                        "severity": "breaking",
                        "location": location,
                        "message": message,
                    }
                )

        for key, old in sorted(old_ops.items()):
            method, path = key
            location = method + " " + path
            new = new_ops.get(key)
            if new is None:
                add("OPERATION_REMOVED", location, "An existing API operation was removed.")
                continue
            old_parameter_list = old.get("parameters", [])
            new_parameter_list = new.get("parameters", [])
            old_params = {
                (item.get("in", ""), item.get("name", "")): item
                for item in old_parameter_list
                if isinstance(old_parameter_list, list) and isinstance(item, dict)
            }
            new_params = {
                (item.get("in", ""), item.get("name", "")): item
                for item in new_parameter_list
                if isinstance(new_parameter_list, list) and isinstance(item, dict)
            }
            for parameter_key, old_param in old_params.items():
                label = location + " parameter " + str(parameter_key)
                new_param = new_params.get(parameter_key)
                if new_param is None:
                    add("PARAMETER_REMOVED", label, "An existing request parameter was removed.")
                    continue
                if not old_param.get("required", False) and new_param.get("required", False):
                    add("REQUIRED_PARAMETER_ADDED", label, "An optional parameter became required.")
                old_type = old_param.get("schema", {}).get("type") if isinstance(old_param.get("schema"), dict) else None
                new_type = new_param.get("schema", {}).get("type") if isinstance(new_param.get("schema"), dict) else None
                if old_type and new_type and old_type != new_type:
                    add("PARAMETER_SCHEMA_CHANGED", label, "The parameter schema type changed.")
            old_responses = old.get("responses", {})
            new_responses = new.get("responses", {})
            if isinstance(old_responses, dict) and isinstance(new_responses, dict):
                for code in sorted(set(old_responses) - set(new_responses)):
                    add("RESPONSE_CODE_REMOVED", location + " response " + code, "An existing response code was removed.")
            old_body = old.get("requestBody", {})
            new_body = new.get("requestBody", {})
            if isinstance(old_body, dict) and isinstance(new_body, dict):
                if not old_body.get("required", False) and new_body.get("required", False):
                    add("REQUEST_BODY_NOW_REQUIRED", location, "The request body became required.")
                old_media = old_body.get("content", {})
                new_media = new_body.get("content", {})
                if isinstance(old_media, dict) and isinstance(new_media, dict):
                    for media in sorted(set(old_media) - set(new_media)):
                        add("REQUEST_MEDIA_TYPE_REMOVED", location + " " + media, "A previously accepted request media type was removed.")

        before_components = before.get("components", {})
        after_components = after.get("components", {})
        old_schemas = before_components.get("schemas", {}) if isinstance(before_components, dict) else {}
        new_schemas = after_components.get("schemas", {}) if isinstance(after_components, dict) else {}
        if not isinstance(old_schemas, dict):
            old_schemas = {}
        if not isinstance(new_schemas, dict):
            new_schemas = {}
        for schema_name, old_schema in sorted(old_schemas.items()):
            location = "components.schemas." + schema_name
            new_schema = new_schemas.get(schema_name)
            if not isinstance(new_schema, dict):
                add("COMPONENT_SCHEMA_REMOVED", location, "An existing component schema was removed.")
                continue
            old_properties = old_schema.get("properties", {}) if isinstance(old_schema, dict) else {}
            new_properties = new_schema.get("properties", {})
            if isinstance(old_properties, dict) and isinstance(new_properties, dict):
                for prop in sorted(set(old_properties) - set(new_properties)):
                    add("SCHEMA_PROPERTY_REMOVED", location + "." + prop, "An existing schema property was removed.")
                for prop in sorted(set(old_properties) & set(new_properties)):
                    old_prop = old_properties[prop]
                    new_prop = new_properties[prop]
                    if isinstance(old_prop, dict) and isinstance(new_prop, dict):
                        old_type = old_prop.get("type")
                        new_type = new_prop.get("type")
                        if old_type and new_type and old_type != new_type:
                            add("SCHEMA_PROPERTY_TYPE_CHANGED", location + "." + prop, "A schema property type changed.")
                        old_enum_values = old_prop.get("enum", [])
                        new_enum_values = new_prop.get("enum", [])
                        old_enum = (
                            {json.dumps(value, sort_keys=True) for value in old_enum_values}
                            if isinstance(old_enum_values, list)
                            else set()
                        )
                        new_enum = (
                            {json.dumps(value, sort_keys=True) for value in new_enum_values}
                            if isinstance(new_enum_values, list)
                            else set()
                        )
                        if old_enum and new_enum and old_enum - new_enum:
                            add("ENUM_VALUES_REMOVED", location + "." + prop, "One or more previously valid enum values were removed.")
            old_required = set(old_schema.get("required", [])) if isinstance(old_schema, dict) else set()
            new_required = set(new_schema.get("required", []))
            for prop in sorted(new_required - old_required):
                if isinstance(new_properties, dict) and prop in new_properties:
                    add("SCHEMA_REQUIRED_PROPERTY_ADDED", location + "." + prop, "A newly required property can break existing clients.")

        return {
            "before_path": before_path,
            "after_path": after_path,
            "before_operation_count": len(old_ops),
            "after_operation_count": len(new_ops),
            "breaking_change_count": len(changes),
            "changes": changes,
            "truncated": len(changes) >= maximum,
            "scope": "shallow_openapi_json_comparison_without_reference_resolution",
        }
