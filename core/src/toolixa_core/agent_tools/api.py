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
