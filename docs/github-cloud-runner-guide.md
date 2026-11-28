# Run Toolixa Agents on GitHub Actions

This workflow runs one registered Toolixa agent on a fresh GitHub-hosted Ubuntu runner. Development, formatting, tests and execution are performed in GitHub; no laptop checkout, self-hosted runner or local Docker environment is required. It does not use the developer's laptop, a self-hosted runner, a local Docker daemon, or the local loopback Gateway.

## Required repository settings

Configure these under the repository's Settings:

| Setting | Type | Example |
|---|---|---|
| TOOLIXA_GATEWAY_URL | Variable | https://your-compatible-gateway.example/v1 |
| TOOLIXA_MODEL | Variable | provider/model-id |
| TOOLIXA_API_KEY | Secret | The API key issued by your HTTPS-compatible endpoint |

The endpoint must expose an OpenAI Chat Completions-compatible API. It must be reachable from GitHub-hosted runners over HTTPS. A laptop address such as 127.0.0.1 or localhost will be rejected. Do not put credentials in the endpoint URL or in repository variables.

No default paid model provider is configured. Configure your own compatible endpoint and key before running the workflow. The GitHub CI tests use fake provider responses and do not consume inference credits.

## Run a task

1. Merge the reviewed Toolixa agent implementation to main.
2. Open the repository's Actions tab.
3. Select Run a registered Toolixa agent.
4. Choose the main branch.
5. Enter a registered ID from catalog/agents.json and a task.
6. Set the reasoning-step, tool-call and wall-clock limits.
7. Start the workflow and read its run summary.

Agent IDs are resolved from the committed catalogue. The runner checks that the selected manifest and entrypoint match the catalogue; unknown IDs fail closed.

## Security model

- The workflow is manual-dispatch only and the job runs only when the selected ref is refs/heads/main.
- Pull-request workflows do not receive TOOLIXA_API_KEY.
- The workflow token has contents: read only. The runner cannot commit, open a PR, or modify the repository.
- The agent is imported only from a catalogue-registered entrypoint; task text is never treated as a Python module, shell command or path.
- Permissions are derived from the registered tools. This runner currently allows workspace.read and security.scan.passive only. Write, shell, process execution, browser automation, arbitrary network fetching and unsupported permissions are rejected.
- The selected agent must complete its configured minimum number of successful tool calls before the runtime can report success.
- Task length is capped at 12000 characters, reasoning steps and tool calls at 25, and wall-clock budget at 180 seconds. Engineering Workflow additionally needs at least three steps and tool calls.
- Result text and diagnostics are redacted before they are written to the Actions log and step summary.
- The remote endpoint must be trusted by the repository owner. Use a dedicated, least-privilege provider key and rotate it if it is exposed.

This is a read-only agent execution workflow, not an autonomous coding or patch-application workflow. The Engineering Workflow can analyze, independently review and produce a test strategy, but it does not write code or execute project tests. Controlled patch approval and isolated execution are separate future capabilities.

## Troubleshooting

- Missing TOOLIXA_GATEWAY_URL or TOOLIXA_MODEL: add the corresponding repository Variable.
- Missing TOOLIXA_API_KEY: create the repository Secret.
- Connection failure: check that the endpoint is public HTTPS and implements compatible chat completions and tool calling.
- Unsupported agent permission: the runner intentionally fails rather than silently granting write, shell or network capabilities.
- Unknown agent ID: check the exact ID in catalog/agents.json and ensure its manifest is committed to main.
