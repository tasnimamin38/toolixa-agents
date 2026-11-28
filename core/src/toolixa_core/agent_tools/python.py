"""Static Python source inspection tools; source is parsed but never executed."""

from __future__ import annotations

import ast
from typing import Any

from toolixa_core.agent_tools.workspace import read_workspace_text
from toolixa_core.logging import redact
from toolixa_core.tools.base import ToolCallContext, ToolSpec


class InspectPythonTool:
    spec = ToolSpec(
        "python.inspect_file",
        "Parse a Python source file without executing it and summarize imports, classes, functions, source locations and structural complexity.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {"path": {"type": "string", "minLength": 1, "maxLength": 500}},
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        relative, source = read_workspace_text(context, arguments["path"])
        if len(source) > 200_000:
            raise ValueError("Python source exceeds the 200,000-character analysis limit")
        try:
            tree = ast.parse(source, filename=relative.as_posix())
        except SyntaxError as exc:
            return {
                "path": relative.as_posix(),
                "syntax_valid": False,
                "syntax_error": {
                    "message": redact(exc.msg)[:200],
                    "line": exc.lineno,
                    "column": exc.offset,
                },
            }

        imports: set[str] = set()
        functions: list[dict[str, Any]] = []
        classes: list[dict[str, Any]] = []
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", maxsplit=1)[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(
                    {"name": node.name, "line": node.lineno, "end_line": node.end_lineno}
                )
            elif isinstance(node, ast.ClassDef):
                classes.append(
                    {"name": node.name, "line": node.lineno, "end_line": node.end_lineno}
                )
            elif isinstance(
                node,
                (
                    ast.If,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.Try,
                    ast.With,
                    ast.BoolOp,
                    ast.IfExp,
                ),
            ):
                complexity += 1

        return {
            "path": relative.as_posix(),
            "syntax_valid": True,
            "imports": sorted(imports),
            "functions": sorted(functions, key=lambda item: (item["line"], item["name"]))[:300],
            "classes": sorted(classes, key=lambda item: (item["line"], item["name"]))[:150],
            "function_count": len(functions),
            "class_count": len(classes),
            "complexity_nodes": complexity,
            "module_docstring": ast.get_docstring(tree) is not None,
            "execution_performed": False,
        }
