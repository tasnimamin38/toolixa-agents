"""Short-lived, single-use in-memory approvals bound to one action and target."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApprovalGrant:
    token: str
    action: str
    target: str
    expires_at: float


class ApprovalManager:
    """An ephemeral approval helper; persistence and remote identity are out of scope."""

    def __init__(self) -> None:
        self._pending: dict[str, ApprovalGrant] = {}

    def issue(self, *, action: str, target: str, ttl_seconds: float = 60.0) -> ApprovalGrant:
        if not action or not target:
            raise ValueError("action and target are required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        grant = ApprovalGrant(
            token=secrets.token_urlsafe(32),
            action=action,
            target=target,
            expires_at=time.monotonic() + ttl_seconds,
        )
        self._pending[grant.token] = grant
        return grant

    def consume(self, token: str, *, action: str, target: str) -> bool:
        grant = self._pending.get(token)
        if grant is None:
            return False
        if grant.expires_at <= time.monotonic():
            self._pending.pop(token, None)
            return False
        if not secrets.compare_digest(grant.action, action):
            return False
        if not secrets.compare_digest(grant.target, target):
            return False
        self._pending.pop(token, None)
        return True
