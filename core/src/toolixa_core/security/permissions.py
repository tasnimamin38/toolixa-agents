"""Canonical permission names. Manifest declarations never grant these by themselves."""

from enum import Enum


class Permission(str, Enum):
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_WRITE = "workspace.write"
    NETWORK_HTTP = "network.http"
    PROCESS_EXECUTE = "process.execute"
    BROWSER_AUTOMATE = "browser.automate"
    SECURITY_SCAN_PASSIVE = "security.scan.passive"
    SECURITY_SCAN_ACTIVE = "security.scan.active"
    PROVIDER_INVOKE = "provider.invoke"
    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"
