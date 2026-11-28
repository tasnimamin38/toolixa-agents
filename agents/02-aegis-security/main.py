"""Passive local source checks with redacted findings."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from toolixa_core.agent_runtime_cli import run_agent_cli
from toolixa_core.agent_tools import PassiveSecurityAuditTool
from toolixa_core.runtime.agent import AgentDefinition

EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}
EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".yml",
    ".yaml",
    ".env",
}
SECRET_ASSIGNMENT = re.compile(
    r"""(?i)\b(api[_-]?key|access[_-]?token|secret|password)\b\s*[:=]\s*['"]?([A-Za-z0-9_./+=-]{16,})"""
)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
RISKY_EVAL = re.compile(r"\b(?:eval|exec)\s*\(")
SHELL_TRUE = re.compile(r"\bshell\s*=\s*True\b")


def scan_text(source: str, file_name: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        if PRIVATE_KEY.search(line):
            findings.append(
                {
                    "file": file_name,
                    "line": line_number,
                    "rule": "PRIVATE_KEY_HEADER",
                    "severity": "critical",
                    "message": "Private key material may be embedded in this file.",
                }
            )
        secret_match = SECRET_ASSIGNMENT.search(line)
        if secret_match:
            value = secret_match.group(2).lower()
            if not any(
                marker in value for marker in ("placeholder", "changeme", "example", "your_")
            ):
                findings.append(
                    {
                        "file": file_name,
                        "line": line_number,
                        "rule": "POSSIBLE_HARDCODED_SECRET",
                        "severity": "high",
                        "message": "A credential-like assignment may contain a hard-coded value.",
                    }
                )
        if file_name.endswith(".py") and RISKY_EVAL.search(line):
            findings.append(
                {
                    "file": file_name,
                    "line": line_number,
                    "rule": "DYNAMIC_EVAL",
                    "severity": "medium",
                    "message": "Dynamic evaluation should be reviewed for untrusted input.",
                }
            )
        if file_name.endswith(".py") and SHELL_TRUE.search(line):
            findings.append(
                {
                    "file": file_name,
                    "line": line_number,
                    "rule": "SUBPROCESS_SHELL_TRUE",
                    "severity": "high",
                    "message": "Shell execution can increase command-injection risk.",
                }
            )
    return findings


def scan_workspace(
    workspace: str | Path, *, max_files: int = 1000, max_bytes: int = 1_000_000
) -> dict[str, object]:
    root = Path(workspace).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace must be a directory")
    if max_files < 1 or max_bytes < 1:
        raise ValueError("scan limits must be positive")

    findings: list[dict[str, object]] = []
    scanned = 0
    truncated = False
    for candidate in sorted(root.rglob("*")):
        if candidate.is_dir():
            continue
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in candidate.parts):
            continue
        if candidate.is_symlink() or candidate.suffix.lower() not in EXTENSIONS:
            continue
        relative = candidate.resolve(strict=True).relative_to(root).as_posix()
        if relative.endswith(".env.example") or candidate.name == ".env.example":
            continue
        if scanned >= max_files:
            truncated = True
            break
        if candidate.stat().st_size > max_bytes:
            continue
        scanned += 1
        try:
            content = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(content, relative))

    return {
        "workspace": str(root),
        "files_scanned": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "truncated": truncated,
        "mode": "passive-local",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--max-files", type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(scan_workspace(args.workspace, max_files=args.max_files), indent=2))



def build_agent() -> AgentDefinition:
    return AgentDefinition(
        id="aegis-security",
        name="Aegis Security",
        system_prompt=(
            "You are a senior application security engineer. Perform a bounded passive review of local source and "
            "configuration evidence using the registered scanner. Explain threat surfaces, likely exploitability, "
            "impact, confidence, false-positive caveats and prioritized remediation. Distinguish pattern matches "
            "from confirmed vulnerabilities. Never repeat secret material, attempt exploitation, perform active "
            "scanning, connect to a target, or claim a full SAST/penetration test was completed. Cite exact file/line "
            "locations returned by the tool and state the scan limits."
        ),
        tools=(PassiveSecurityAuditTool(),),
        min_tool_calls=1,
    )


if __name__ == "__main__":
    raise SystemExit(run_agent_cli(build_agent(), description=__doc__ or "02-aegis-security"))
