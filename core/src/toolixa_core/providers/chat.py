"""HTTPX client for the local Toolixa Gateway's OpenAI-compatible API."""

from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit, urlunsplit

import httpx

from toolixa_core.providers.base import ProviderError


def _validate_gateway_url(value: str) -> str:
    candidate = value.strip()
    if not candidate or any(ord(char) < 32 for char in candidate):
        raise ProviderError("gateway URL is required and must not contain control characters")
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ProviderError("gateway URL must be an absolute HTTP(S) API base URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProviderError("gateway URL cannot contain credentials, query strings, or fragments")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ProviderError("gateway URL contains an invalid port") from exc

    host = parsed.hostname.rstrip(".").lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    loopback = host == "localhost" or (address is not None and address.is_loopback)
    if parsed.scheme == "http" and not loopback:
        raise ProviderError("unencrypted gateway HTTP is allowed only on loopback")
    if address is not None and not address.is_global and not loopback:
        raise ProviderError("gateway URL cannot point to a private or reserved IP address")

    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


class GatewayChatClient:
    """Synchronous, bounded client for a locally configured Toolixa Gateway."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        model: str = "",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderError("a Toolixa gateway API key is required")
        if len(api_key) > 256 or any(char.isspace() for char in api_key):
            raise ProviderError("Toolixa gateway API key has an invalid format")
        self.base_url = _validate_gateway_url(base_url)
        self.api_key = api_key.strip()
        self.model = model.strip()
        self._transport = transport

    @classmethod
    def from_env(cls) -> GatewayChatClient:
        """Build a client from local process settings without printing secrets."""
        api_key = os.environ.get("TOOLIXA_API_KEY", "").strip()
        model = os.environ.get("TOOLIXA_MODEL", "").strip()
        base_url = os.environ.get("TOOLIXA_GATEWAY_URL", "http://127.0.0.1:20128/v1").strip()
        if not api_key:
            raise ProviderError("TOOLIXA_API_KEY is required; create a key in the local dashboard")
        if not model:
            raise ProviderError(
                "TOOLIXA_MODEL is required; choose a model from the local dashboard"
            )
        return cls(base_url, api_key, model=model)

    def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        timeout_seconds: float,
    ) -> dict[str, object]:
        if not model.strip():
            raise ProviderError("a model ID is required")
        if not isinstance(messages, list) or not messages:
            raise ProviderError("at least one chat message is required")
        if not isinstance(tools, list):
            raise ProviderError("tools must be a list")
        if timeout_seconds <= 0:
            raise ProviderError("timeout_seconds must be positive")

        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2048,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            with httpx.Client(
                timeout=httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 8.0)),
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"gateway request failed: {type(exc).__name__}") from exc

        if response.is_error:
            message = f"gateway returned HTTP {response.status_code}"
            try:
                body = response.json()
                error = body.get("error", body) if isinstance(body, dict) else body
                if isinstance(error, dict):
                    detail = error.get("message") or error.get("detail")
                else:
                    detail = str(error)
                if detail:
                    message = str(detail)[:300]
            except (ValueError, TypeError):
                pass
            message = message.replace(self.api_key, "[REDACTED]")
            raise ProviderError(message)

        try:
            result = response.json()
        except ValueError as exc:
            raise ProviderError("gateway returned invalid JSON") from exc
        if not isinstance(result, dict):
            raise ProviderError("gateway response must be a JSON object")
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderError("gateway response has no valid completion choice")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ProviderError("gateway completion choice has no message object")
        return result
