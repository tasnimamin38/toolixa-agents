# Toolixa Security Model

## Threat model

Toolixa agents may process untrusted source files, HTML, retrieved documents, prompts, provider responses, and task descriptions. Risks include prompt injection, accidental data disclosure, path traversal, SSRF, excessive execution, secret leakage, and unsafe agent delegation.

## Defaults

- No permission is granted merely because a manifest declares it.
- No shell/process execution is available through the default executor.
- Active security scanning is disabled unless an explicit target grant is provided.
- Workspace read/write operations must be constrained to operator-configured roots.
- Network access requires an explicit permission and exact host allowlist.
- Provider credentials must not appear in source, manifests, catalogs, logs, traces, or reports.
- The first Web Scraper parses local HTML files; it does not make HTTP requests.

## Permission names

workspace.read, workspace.write, network.http, process.execute, browser.automate, security.scan.passive, security.scan.active, provider.invoke, memory.read, and memory.write are canonical capability names.

Grants are request-scoped. The tool registry checks required permissions before invoking a registered tool. Tools that access a specific path or URL must additionally check the actual target. Active scan permission is bound to an allowlisted target.

## Approvals

ApprovalManager provides in-process, short-lived, single-use tokens bound to one action and target. It is a building block, not an identity provider or durable approval database. Applications that need remote or persistent approvals must provide their own authenticated approval system.

## Execution isolation

DisabledExecutor is the only built-in executor. It always refuses process execution. Any future executor adapter must document and enforce its isolation boundary, non-root identity, read-only mounts where possible, CPU/memory/process/time limits, restricted network egress, and secret isolation.

A container alone is not a complete security boundary. Do not mount the Docker socket, host credentials, home directory, or privileged host resources into an agent container.

## SSRF and web fetching

Network-enabled crawling is deliberately not implemented in this baseline. A future HTTP fetcher must pin the validated resolved address to the actual connection or rely on an enforced egress proxy/firewall, re-check every redirect, reject loopback/private/link-local/multicast/reserved/metadata addresses, and test DNS rebinding. A preflight DNS lookup followed by an ordinary second DNS lookup in the HTTP client is not sufficient.

## RAG prompt injection

Retrieved passages are untrusted content. Keep system policy separate from retrieved text, show document source ranges, and never execute instructions embedded in documents.

## Logging

Use the redaction helper as one layer only. Avoid logging full request bodies, environment dumps, authorization headers, or source lines that may contain secrets. The local approval manager and logs are not tamper-proof.
