# Bring Your Own Runtime (BYOR) and Bring Your Own Key (BYOK)

## BYOR

BYOR means the developer chooses where the agent process runs: a local virtual environment, a developer-managed container, or an independently operated server. Toolixa does not supply a central execution service.

The initial release does not include a production sandbox executor. Shell execution is disabled by default. Do not run untrusted code on a workstation that contains personal files, production credentials, or privileged cloud access.

## BYOK

BYOK means provider credentials are supplied by the operator, not embedded in Toolixa. Configure the selected provider in its own adapter and keep credentials in environment variables or a local secret manager.

Never commit actual keys. The repository includes placeholders only in .env.example files. Do not print the environment or serialize credentials into request objects.

## Development installation

1. Create a Python 3.11+ virtual environment.
2. Install core with python -m pip install -e ./core.
3. Install only the selected agent's requirements.
4. Read the selected agent README and manifest.
5. Start with a temporary workspace and no optional permissions.
6. Add a provider adapter only when the selected operation requires one.

## Provider behavior

Core provides a provider protocol and registry. Vendor SDKs are optional and are not imported by core. A missing provider configuration must produce an explicit error; no hidden fallback to a different provider is allowed.
