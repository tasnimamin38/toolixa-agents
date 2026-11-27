"""Validate agent manifests and build the static website catalog."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path("catalog/agents.json")
VALID_PERMISSIONS = {
    "workspace.read",
    "workspace.write",
    "network.http",
    "process.execute",
    "browser.automate",
    "security.scan.passive",
    "security.scan.active",
    "provider.invoke",
    "memory.read",
    "memory.write",
}
REPOSITORY = "tasnimamin38/toolixa-agents"


def build_catalog(root: Path = ROOT) -> dict[str, Any]:
    agent_root = root / "agents"
    if not agent_root.is_dir():
        raise ValueError("agents directory is missing")
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for manifest_path in sorted(agent_root.glob("*/agent.json")):
        agent_dir = manifest_path.parent
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError(f"{manifest_path}: manifest must be a JSON object")
        required = {
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
        missing = sorted(required - manifest.keys())
        if missing:
            raise ValueError(f"{manifest_path}: missing fields: {', '.join(missing)}")
        if manifest["schema_version"] != 1:
            raise ValueError(f"{manifest_path}: unsupported schema_version")
        agent_id = manifest["id"]
        if not isinstance(agent_id, str) or not agent_id or agent_id in seen_ids:
            raise ValueError(f"{manifest_path}: invalid or duplicate agent id")
        seen_ids.add(agent_id)
        if manifest["status"] not in {"experimental", "beta", "stable"}:
            raise ValueError(f"{manifest_path}: invalid status")
        for field in ("dependencies", "capabilities", "permissions"):
            if not isinstance(manifest[field], list) or not all(
                isinstance(item, str) for item in manifest[field]
            ):
                raise ValueError(f"{manifest_path}: {field} must be a list of strings")
        unknown_permissions = sorted(set(manifest["permissions"]) - VALID_PERMISSIONS)
        if unknown_permissions:
            raise ValueError(
                f"{manifest_path}: unknown permissions: {', '.join(unknown_permissions)}"
            )

        for field in ("entrypoint", "documentation"):
            relative = Path(manifest[field])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"{manifest_path}: {field} must stay inside the agent directory")
            target = (agent_dir / relative).resolve(strict=True)
            try:
                target.relative_to(agent_dir.resolve(strict=True))
            except ValueError as exc:
                raise ValueError(f"{manifest_path}: {field} escapes agent directory") from exc
            if not target.is_file():
                raise ValueError(f"{manifest_path}: {field} must reference a file")

        relative_dir = agent_dir.relative_to(root).as_posix()
        entries.append(
            {
                "id": agent_id,
                "name": manifest["name"],
                "version": manifest["version"],
                "category": manifest["category"],
                "description": manifest["description"],
                "status": manifest["status"],
                "capabilities": manifest["capabilities"],
                "permissions": manifest["permissions"],
                "dependencies": manifest["dependencies"],
                "python": manifest["python"],
                "path": relative_dir,
                "entrypoint": manifest["entrypoint"],
                "documentation": manifest["documentation"],
            }
        )

    if not entries:
        raise ValueError("no agent manifests found")
    return {"schema_version": 1, "repository": REPOSITORY, "agents": entries}


def catalog_text(root: Path = ROOT) -> str:
    return json.dumps(build_catalog(root), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail if the committed catalog is stale"
    )
    args = parser.parse_args()
    output_path = ROOT / OUTPUT
    expected = catalog_text()
    if args.check:
        if not output_path.is_file():
            print("catalog is missing; run python scripts/build_catalog.py", file=sys.stderr)
            return 1
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            print("catalog is stale; run python scripts/build_catalog.py", file=sys.stderr)
            return 1
        print("catalog is valid and up to date")
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(expected, encoding="utf-8")
    print(f"wrote {output_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())