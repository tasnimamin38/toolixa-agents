"""Static Python source-to-test mapping without executing application or test code."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from toolixa_core.agent_tools.workspace import is_excluded_path, workspace_root
from toolixa_core.tools.base import ToolCallContext, ToolSpec

_TEST_DIRS = {"test", "tests"}


def _module_name(relative: Path) -> str:
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _is_test_file(relative: Path) -> bool:
    return any(part.casefold() in _TEST_DIRS for part in relative.parts[:-1]) or (
        relative.name.startswith("test_") or relative.name.endswith("_test.py")
    )


class _SourceSymbolVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.classes: list[str] = []
        self.symbols: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = ".".join([*self.classes, node.name])
        self.symbols.append({"symbol": qualified, "kind": "class", "line": node.lineno})
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        qualified = ".".join([*self.classes, node.name])
        kind = "method" if self.classes else "function"
        self.symbols.append({"symbol": qualified, "kind": kind, "line": node.lineno})
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


class _TestReferenceVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.current_class: list[str] = []
        self.tests: list[dict[str, Any]] = []
        self.imported_modules: set[str] = set()
        self.imported_names: set[str] = set()
        self._current_test: dict[str, Any] | None = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.current_class.append(node.name)
        self.generic_visit(node)
        self.current_class.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        previous = self._current_test
        if node.name.startswith("test_"):
            self._current_test = {
                "name": node.name,
                "qualified": ".".join([*self.current_class, node.name]),
                "line": node.lineno,
                "names": set(self.imported_names),
                "modules": set(self.imported_modules),
            }
            self.tests.append(self._current_test)
        self.generic_visit(node)
        self._current_test = previous

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Name(self, node: ast.Name) -> None:
        if self._current_test is not None:
            self._current_test["names"].add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self._current_test is not None:
            self._current_test["names"].add(node.attr)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imported_modules.add(alias.name)
            self.imported_names.add(alias.asname or alias.name.split(".")[0])
        if self._current_test is not None:
            self._current_test["modules"].update(self.imported_modules)
            self._current_test["names"].update(self.imported_names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imported_modules.add(node.module)
        for alias in node.names:
            self.imported_names.add(alias.asname or alias.name)
        if self._current_test is not None:
            self._current_test["modules"].update(self.imported_modules)
            self._current_test["names"].update(self.imported_names)


class MapPythonTestCoverageTool:
    spec = ToolSpec(
        "qa.map_python_test_coverage",
        "Statically map Python functions, classes and methods to pytest-style test functions using imports, symbol references and test naming. Identifies likely untested symbols; it does not execute tests or measure runtime coverage.",
        ("workspace.read",),
        {
            "type": "object",
            "properties": {
                "max_files": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_symbols": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        root = workspace_root(context)
        max_files = arguments.get("max_files", 300)
        max_symbols = arguments.get("max_symbols", 1000)
        if not 1 <= max_files <= 500:
            raise ValueError("max_files must be between 1 and 500")
        if not 1 <= max_symbols <= 1000:
            raise ValueError("max_symbols must be between 1 and 1000")

        source_modules: dict[str, tuple[str, list[dict[str, Any]]]] = {}
        test_records: list[dict[str, Any]] = []
        parse_errors: list[dict[str, Any]] = []
        scanned = 0
        truncated = False
        for path in sorted(root.rglob("*.py")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root)
            if is_excluded_path(relative) or path.stat().st_size > 500_000:
                continue
            if scanned >= max_files:
                truncated = True
                break
            scanned += 1
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8"), filename=relative.as_posix()
                )
            except (OSError, UnicodeDecodeError):
                continue
            except SyntaxError as exc:
                parse_errors.append(
                    {
                        "path": relative.as_posix(),
                        "line": exc.lineno,
                        "message": exc.msg[:160],
                    }
                )
                continue

            if _is_test_file(relative):
                visitor = _TestReferenceVisitor()
                visitor.visit(tree)
                module = _module_name(relative)
                for item in visitor.tests:
                    test_records.append(
                        {
                            "path": relative.as_posix(),
                            "module": module,
                            "name": item["name"],
                            "qualified": item["qualified"],
                            "line": item["line"],
                            "names": item["names"],
                            "modules": item["modules"],
                        }
                    )
            else:
                visitor = _SourceSymbolVisitor()
                visitor.visit(tree)
                if visitor.symbols:
                    source_modules[_module_name(relative)] = (
                        relative.as_posix(),
                        visitor.symbols,
                    )

        symbols: list[dict[str, Any]] = []
        for module, (path, definitions) in sorted(source_modules.items()):
            for definition in definitions:
                leaf = definition["symbol"].split(".")[-1]
                references: list[str] = []
                for record in test_records:
                    module_matches = (
                        module in record["modules"]
                        or any(module.startswith(item + ".") for item in record["modules"])
                        or any(item.startswith(module + ".") for item in record["modules"])
                    )
                    file_stem = Path(record["path"]).stem
                    inferred_module = file_stem.removeprefix("test_").removesuffix("_test")
                    filename_matches = inferred_module == Path(path).stem
                    if not module_matches and not filename_matches:
                        continue
                    names = record["names"]
                    if (
                        definition["symbol"] in names
                        or leaf in names
                        or record["name"].endswith(leaf)
                    ):
                        references.append(f'{record["path"]}::{record["qualified"]}')
                symbols.append(
                    {
                        "path": path,
                        "symbol": definition["symbol"],
                        "kind": definition["kind"],
                        "line": definition["line"],
                        "tests": sorted(set(references)),
                        "coverage_state": (
                            "test_reference_found" if references else "no_test_reference_found"
                        ),
                    }
                )
                if len(symbols) >= max_symbols:
                    truncated = True
                    break
            if truncated and len(symbols) >= max_symbols:
                break

        uncovered = sum(
            item["coverage_state"] == "no_test_reference_found" for item in symbols
        )
        return {
            "source_module_count": len(source_modules),
            "source_symbol_count": len(symbols),
            "test_function_count": len(test_records),
            "symbols_without_test_reference": uncovered,
            "static_reference_coverage_percent": (
                round((len(symbols) - uncovered) / len(symbols) * 100, 2)
                if symbols
                else None
            ),
            "symbols": symbols,
            "parse_errors": parse_errors[:100],
            "truncated": truncated,
            "tests_executed": False,
            "runtime_coverage_measured": False,
        }
