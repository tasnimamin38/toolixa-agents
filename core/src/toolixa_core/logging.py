"""Small secret-redaction helper for structured logging."""

from __future__ import annotations

import re
from collections.abc import Iterable

_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"(?i)((?:api[_-]?key|secret|token|password)\s*[:=]\s*)['\"]?[^\s'\"]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
)


def redact(value: str, *, known_secrets: Iterable[str] = ()) -> str:
    """Redact common credential shapes and explicitly supplied secret values."""
    result = value
    for secret in known_secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    for pattern in _PATTERNS:
        result = pattern.sub(
            lambda match: (match.group(1) if match.lastindex else "") + "[REDACTED]",
            result,
        )
    return result
