"""Static Python source inspection tools; source is parsed but never executed."""

from __future__ import annotations

import ast
from pathlib import Path
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


class AnalyzePythonModuleGraphTool:
    spec = ToolSpec(
        "python.analyze_module_graph",
        "Build a bounded static import graph for local Python modules and detect strongly connected import cycles. Files are parsed as AST only and never executed.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "max_files": {"type": "integer", "minimum": 1, "maximum": 500},
            },
            "additionalProperties": False,
        },
    )

    @staticmethod
    def _module_name(relative: Path) -> str:
        without_suffix = relative.with_suffix("")
        parts = list(without_suffix.parts)
        if parts and parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        from toolixa_core.agent_tools.workspace import is_excluded_path, workspace_root

        root = workspace_root(context)
        maximum = arguments.get("max_files", 250)
        if not 1 <= maximum <= 500:
            raise ValueError("max_files must be between 1 and 500")
        candidates = []
        truncated = False
        for path in sorted(root.rglob("*.py")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root)
            if is_excluded_path(relative) or path.stat().st_size > 200_000:
                continue
            if len(candidates) >= maximum:
                truncated = True
                break
            candidates.append((relative, path))
        modules = {self._module_name(relative): (relative, path) for relative, path in candidates}
        graph: dict[str, set[str]] = {name: set() for name in modules}
        external: set[str] = set()
        parse_errors: list[dict[str, Any]] = []
        for module_name, (relative, path) in modules.items():
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative.as_posix())
            except (OSError, UnicodeDecodeError):
                continue
            except SyntaxError as exc:
                parse_errors.append(
                    {
                        "path": relative.as_posix(),
                        "line": exc.lineno,
                        "message": redact(exc.msg)[:160],
                    }
                )
                continue
            package_parts = (
                module_name.split(".")
                if relative.name == "__init__.py"
                else module_name.split(".")[:-1]
            )
            for node in ast.walk(tree):
                imports: list[str] = []
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    base_parts = list(package_parts)
                    if node.level:
                        remove_count = node.level - 1
                        if remove_count > len(base_parts):
                            continue
                        if remove_count:
                            base_parts = base_parts[:-remove_count]
                        if node.module:
                            base_parts.extend(node.module.split("."))
                        base = ".".join(base_parts)
                    else:
                        base = node.module or ""
                    if base:
                        imports.append(base)
                        for alias in node.names:
                            candidate = base + "." + alias.name
                            if candidate in modules:
                                imports.append(candidate)
                for imported in imports:
                    if imported in modules:
                        graph[module_name].add(imported)
                    else:
                        top_level = imported.split(".", 1)[0]
                        if not any(
                            name == imported or name.startswith(imported + ".") for name in modules
                        ):
                            external.add(top_level)

        state: dict[str, int] = {}
        stack: list[str] = []
        cycles: set[tuple[str, ...]] = set()

        def visit(node: str) -> None:
            state[node] = 1
            stack.append(node)
            for dependency in sorted(graph[node]):
                if state.get(dependency, 0) == 0:
                    visit(dependency)
                elif state.get(dependency) == 1:
                    cycle_start = stack.index(dependency)
                    cycle = tuple(sorted(stack[cycle_start:]))
                    if len(cycle) > 1:
                        cycles.add(cycle)
            stack.pop()
            state[node] = 2

        for module_name in sorted(graph):
            if state.get(module_name, 0) == 0:
                visit(module_name)
        edges = [
            {"from": module_name, "to": dependency}
            for module_name in sorted(graph)
            for dependency in sorted(graph[module_name])
        ]
        return {
            "module_count": len(modules),
            "edge_count": len(edges),
            "modules": sorted(modules),
            "edges": edges[:1000],
            "cycles": [list(item) for item in sorted(cycles)],
            "cycle_count": len(cycles),
            "external_imports": sorted(external)[:200],
            "parse_errors": parse_errors[:100],
            "truncated": truncated,
            "execution_performed": False,
        }
