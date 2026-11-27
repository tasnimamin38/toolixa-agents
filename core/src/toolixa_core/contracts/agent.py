"""Manifest loader for agent discovery and validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_AGENT_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REQUIRED = {
    "schema_version",
    "id",
    "name",
    "version",
    "category",
    "description",
    "entrypoint",
    "python",
    "dependencies",
    "capabilities",
    "permissions",
    "status",
    "documentation",
}


@dataclass(frozen=True, slots=True)
class AgentManifest:
    schema_version: int
    id: str
    name: str
    version: str
    category: str
    description: str
    entrypoint: str
    python: str
    dependencies: tuple[str, ...]
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    status: str
    documentation: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> AgentManifest:
        missing = sorted(_REQUIRED - data.keys())
        if missing:
            raise ValueError(f"manifest is missing required fields: {', '.join(missing)}")
        if data["schema_version"] != 1:
            raise ValueError("unsupported manifest schema_version")
        if not isinstance(data["id"], str) or not _AGENT_ID.fullmatch(data["id"]):
            raise ValueError("id must be a lowercase kebab-case identifier")
        if data["status"] not in {"experimental", "beta", "stable"}:
            raise ValueError("status must be experimental, beta, or stable")
        for field_name in ("dependencies", "capabilities", "permissions"):
            value = data[field_name]
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"{field_name} must be a list of strings")
        for field_name in ("entrypoint", "documentation"):
            value = data[field_name]
            if not isinstance(value, str) or not value or Path(value).is_absolute():
                raise ValueError(f"{field_name} must be a relative path")
            if ".." in Path(value).parts:
                raise ValueError(f"{field_name} cannot traverse parent directories")
        for field_name in ("name", "version", "category", "description", "python"):
            if not isinstance(data[field_name], str) or not data[field_name].strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        return cls(
            schema_version=data["schema_version"],
            id=data["id"],
            name=data["name"],
            version=data["version"],
            category=data["category"],
            description=data["description"],
            entrypoint=data["entrypoint"],
            python=data["python"],
            dependencies=tuple(data["dependencies"]),
            capabilities=tuple(data["capabilities"]),
            permissions=tuple(data["permissions"]),
            status=data["status"],
            documentation=data["documentation"],
        )


def load_manifest(path: str | Path) -> AgentManifest:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("agent manifest root must be a JSON object")
    return AgentManifest.from_mapping(data)
