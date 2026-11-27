# Toolixa Architecture

## System boundary

Toolixa is a source-code catalog plus a small shared Python SDK. The static website discovers agents from catalog/agents.json. Agent execution happens only in a runtime selected and operated by the developer.

~~~text
Developer
  -> Static Agent Directory
  -> Download one agent + compatible toolixa-core package
  -> Configure own provider credentials and local runtime
  -> Agent request
      -> provider adapter (optional)
      -> permission-aware tool registry
      -> explicit policy / approval gate
      -> configured executor (disabled by default)
      -> structured result + redacted audit event
~~~

## Package boundaries

- core/src/toolixa_core/contracts defines request, result, manifest, and budget types.
- providers defines a protocol and explicit registry; no provider is selected implicitly.
- tools defines metadata, context, and a registry that checks required permissions.
- security defines permission names, deny-by-default decisions, and ephemeral one-use approvals.
- runtime defines resource budgets and a disabled-by-default executor protocol.
- memory defines a storage protocol and source-aware document chunks.
- Each agents/* directory owns its entry point, manifest, README, tests, and direct dependencies.

## Data flow and trust

Agent manifests are declarations, not grants. Runtime permissions are supplied by the operator for a request. Provider responses, fetched pages, and retrieved documents are untrusted data. They never become higher-priority instructions.

The first agent release is intentionally local-first. No service is required for normal local analysis, document lookup, task ordering, content brief preparation, or parsing a supplied HTML file.

## Distribution

Install toolixa-core in editable mode for monorepo development with python -m pip install -e ./core. Install only the chosen agent's requirements. A standalone agent archive must pin or bundle a compatible core distribution; copying one folder while omitting its declared core dependency is not a complete release.

## Scaling

New agents are added by introducing a manifest, documentation, a bounded entry point, isolated dependencies, and tests. The catalog generator discovers manifests without importing or executing agents. Core contracts change only when a genuinely shared interface is needed.
