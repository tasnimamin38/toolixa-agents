"""Non-secret runtime configuration loaded from explicit environment names."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ToolixaSettings:
    provider: str | None = None
    model: str | None = None
    workspace: Path | None = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> ToolixaSettings:
        values = os.environ if environ is None else environ
        provider = values.get("TOOLIXA_PROVIDER") or None
        model = values.get("TOOLIXA_MODEL") or None
        workspace_value = values.get("TOOLIXA_WORKSPACE") or None
        log_level = values.get("TOOLIXA_LOG_LEVEL", "INFO").upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("TOOLIXA_LOG_LEVEL is invalid")
        workspace = Path(workspace_value).expanduser() if workspace_value else None
        return cls(provider=provider, model=model, workspace=workspace, log_level=log_level)
