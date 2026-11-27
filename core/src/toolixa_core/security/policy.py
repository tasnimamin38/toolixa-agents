"""Deny-by-default request-scoped permission policy."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


class PermissionDenied(PermissionError):
    """Raised when a requested operation is not explicitly authorized."""


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    permission: str
    reason: str


@dataclass(frozen=True, slots=True)
class RuntimePolicy:
    granted_permissions: frozenset[str] = field(default_factory=frozenset)
    workspace_roots: tuple[Path, ...] = ()
    allowed_hosts: frozenset[str] = field(default_factory=frozenset)
    active_scan_targets: frozenset[str] = field(default_factory=frozenset)

    def decide(self, permission: str, *, target: str | Path | None = None) -> PolicyDecision:
        if permission not in self.granted_permissions:
            return PolicyDecision(False, permission, "permission was not granted")

        if permission in {"workspace.read", "workspace.write"}:
            if target is None or not self._inside_workspace(Path(target)):
                return PolicyDecision(False, permission, "path is outside approved workspace roots")

        if permission == "network.http":
            if target is None or not self._allowed_network_target(str(target)):
                return PolicyDecision(False, permission, "network target is not explicitly allowed")

        if permission == "security.scan.active":
            if target is None or str(target).lower() not in self.active_scan_targets:
                return PolicyDecision(False, permission, "active scan target is not allowlisted")

        return PolicyDecision(True, permission, "explicit grant and target policy passed")

    def require(self, permission: str, *, target: str | Path | None = None) -> None:
        decision = self.decide(permission, target=target)
        if not decision.allowed:
            raise PermissionDenied(decision.reason)

    def _inside_workspace(self, path: Path) -> bool:
        candidate = path.expanduser().resolve(strict=False)
        for root in self.workspace_roots:
            resolved_root = root.expanduser().resolve(strict=False)
            try:
                candidate.relative_to(resolved_root)
                return True
            except ValueError:
                continue
        return False

    def _allowed_network_target(self, value: str) -> bool:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        host = parsed.hostname.rstrip(".").lower()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return False
        return host in self.allowed_hosts
