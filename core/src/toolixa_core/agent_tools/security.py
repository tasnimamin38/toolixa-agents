"""Bounded passive source-security checks with non-sensitive findings only."""

from __future__ import annotations

import ast
import re
from typing import Any

from toolixa_core.agent_tools.workspace import is_excluded_path, workspace_root
from toolixa_core.tools.base import ToolCallContext, ToolSpec

_PATTERNS = (
    (
        "POSSIBLE_HARDCODED_CREDENTIAL",
        "high",
        "Credential-like assignment detected; matched value withheld.",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\b\s*[:=]\s*['"][^'"]{8,}['"]"""
        ),
    ),
    (
        "PRIVATE_KEY_HEADER",
        "critical",
        "Private-key header detected; key material withheld.",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "PYTHON_DYNAMIC_EVAL",
        "medium",
        "Dynamic Python evaluation requires review.",
        re.compile(r"\b(?:eval|exec)\s*\("),
    ),
    (
        "SUBPROCESS_SHELL_TRUE",
        "high",
        "Shell-enabled subprocess execution requires review.",
        re.compile(r"\bshell\s*=\s*True\b"),
    ),
    (
        "TLS_VERIFICATION_DISABLED",
        "high",
        "TLS certificate verification appears disabled.",
        re.compile(r"(?i)\bverify\s*=\s*False\b"),
    ),
)
_SUFFIXES = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
    ".html",
    ".sh",
    ".ps1",
}


class PassiveSecurityAuditTool:
    spec = ToolSpec(
        "security.audit_source",
        "Passively scan bounded local source/configuration files for selected credential and unsafe-code patterns. Never returns matched values or performs active scans.",
        ("workspace.read", "security.scan.passive"),
        {
            "type": "object",
            "properties": {
                "max_files": {"type": "integer", "minimum": 1, "maximum": 500},
                "max_file_bytes": {"type": "integer", "minimum": 1, "maximum": 262144},
                "max_findings": {"type": "integer", "minimum": 1, "maximum": 500},
            },
            "additionalProperties": False,
        },
    )

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        root = workspace_root(context)
        max_files = arguments.get("max_files", 250)
        max_bytes = arguments.get("max_file_bytes", 131072)
        max_findings = arguments.get("max_findings", 200)
        if not 1 <= max_files <= 500:
            raise ValueError("max_files must be between 1 and 500")
        if not 1 <= max_bytes <= 262144:
            raise ValueError("max_file_bytes must be between 1 and 262144")
        if not 1 <= max_findings <= 500:
            raise ValueError("max_findings must be between 1 and 500")
        scanned = 0
        findings = []
        truncated = False
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root)
            if is_excluded_path(relative) or path.suffix.lower() not in _SUFFIXES:
                continue
            if scanned >= max_files:
                truncated = True
                break
            try:
                if path.stat().st_size > max_bytes:
                    continue
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            scanned += 1
            for line_number, line in enumerate(lines, 1):
                for rule, severity, message, pattern in _PATTERNS:
                    if (
                        rule in {"PYTHON_DYNAMIC_EVAL", "SUBPROCESS_SHELL_TRUE"}
                        and path.suffix.lower() != ".py"
                    ):
                        continue
                    if pattern.search(line):
                        findings.append(
                            {
                                "rule_id": rule,
                                "severity": severity,
                                "path": relative.as_posix(),
                                "line": line_number,
                                "message": message,
                            }
                        )
                        if len(findings) >= max_findings:
                            truncated = True
                            break
                if truncated and len(findings) >= max_findings:
                    break
            if truncated and len(findings) >= max_findings:
                break
        return {
            "scope": "passive_local_source_only",
            "files_scanned": scanned,
            "finding_count": len(findings),
            "findings": findings,
            "truncated": truncated,
            "secret_values_returned": False,
            "network_requests": 0,
        }


class PythonSecurityASTTool:
    spec = ToolSpec(
        "security.inspect_python_ast",
        "Parse Python source without execution and detect risky dynamic execution, unsafe deserialization, shell-enabled subprocesses, unsafe YAML loading, insecure temporary files, disabled TLS verification and weak hashes. Findings contain rule IDs and locations, never source lines.",
        ("workspace.read", "security.scan.passive"),
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "minLength": 1, "maxLength": 500},
                "max_findings": {"type": "integer", "minimum": 1, "maximum": 300},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    @staticmethod
    def _name(node: ast.AST) -> str:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def invoke(self, arguments: dict[str, Any], context: ToolCallContext) -> dict[str, Any]:
        relative, source = read_workspace_text(context, arguments["path"], max_bytes=200_000)
        maximum = arguments.get("max_findings", 200)
        if not 1 <= maximum <= 300:
            raise ValueError("max_findings must be between 1 and 300")
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
                "findings": [],
                "finding_count": 0,
                "source_code_returned": False,
            }

        findings: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = self._name(node.func)
            rule: tuple[str, str, str] | None = None
            if name in {"eval", "exec", "compile"}:
                rule = (
                    "PYTHON_DYNAMIC_EVAL",
                    "high",
                    "Dynamic code evaluation requires review for untrusted input.",
                )
            elif name in {"pickle.load", "pickle.loads", "marshal.loads"}:
                rule = (
                    "PYTHON_UNSAFE_DESERIALIZATION",
                    "critical",
                    "Unsafe object deserialization can execute attacker-controlled payloads.",
                )
            elif name in {"yaml.unsafe_load"}:
                rule = (
                    "PYTHON_UNSAFE_YAML_LOAD",
                    "critical",
                    "Unsafe YAML loading can instantiate arbitrary Python objects.",
                )
            elif name == "yaml.load":
                loader = next((item.value for item in node.keywords if item.arg == "Loader"), None)
                safe_loader = (
                    isinstance(loader, ast.Attribute)
                    and loader.attr in {"SafeLoader", "CSafeLoader"}
                )
                if not safe_loader:
                    rule = (
                        "PYTHON_UNSAFE_YAML_LOAD",
                        "high",
                        "YAML loading should use SafeLoader or CSafeLoader for untrusted input.",
                    )
            elif name in {"subprocess.run", "subprocess.call", "subprocess.Popen", "subprocess.check_output"}:
                shell = next((item.value for item in node.keywords if item.arg == "shell"), None)
                if isinstance(shell, ast.Constant) and shell.value is True:
                    rule = (
                        "PYTHON_SUBPROCESS_SHELL_TRUE",
                        "critical",
                        "Shell-enabled subprocess execution can create command-injection risk.",
                    )
            elif name in {"os.system", "os.popen"}:
                rule = (
                    "PYTHON_OS_SHELL_EXECUTION",
                    "high",
                    "Direct OS shell execution requires input and privilege review.",
                )
            elif name == "tempfile.mktemp":
                rule = (
                    "PYTHON_INSECURE_TEMPFILE",
                    "high",
                    "mktemp can introduce race conditions; use secure temporary-file APIs.",
                )
            elif name in {"hashlib.md5", "hashlib.sha1"}:
                rule = (
                    "PYTHON_WEAK_HASH",
                    "medium",
                    "MD5 and SHA-1 are unsuitable for collision-resistant security uses.",
                )
            if rule is None:
                for keyword in node.keywords:
                    if (
                        keyword.arg == "verify"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is False
                    ):
                        rule = (
                            "PYTHON_TLS_VERIFY_DISABLED",
                            "high",
                            "TLS certificate verification appears disabled.",
                        )
                        break
            if rule is not None:
                findings.append(
                    {
                        "rule_id": rule[0],
                        "severity": rule[1],
                        "path": relative.as_posix(),
                        "line": getattr(node, "lineno", 1),
                        "column": getattr(node, "col_offset", 0),
                        "message": rule[2],
                    }
                )
                if len(findings) >= maximum:
                    break

        findings.sort(key=lambda item: (item["line"], item["column"], item["rule_id"]))
        return {
            "path": relative.as_posix(),
            "syntax_valid": True,
            "finding_count": len(findings),
            "findings": findings,
            "truncated": len(findings) >= maximum,
            "source_code_returned": False,
            "execution_performed": False,
        }
