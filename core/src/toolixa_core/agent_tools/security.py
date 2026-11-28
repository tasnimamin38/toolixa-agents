"""Bounded passive source-security checks with non-sensitive findings only."""

from __future__ import annotations

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
