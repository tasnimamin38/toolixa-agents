from __future__ import annotations

import json

import httpx
import pytest

from toolixa_core.providers.base import ProviderError
from toolixa_core.providers.chat import GatewayChatClient


def test_gateway_client_sends_model_and_tool_schemas_to_local_api():
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Done"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            },
        )

    client = GatewayChatClient(
        "http://127.0.0.1:20128/v1",
        "tla_test_key",
        transport=httpx.MockTransport(handler),
    )
    result = client.complete(
        model="openrouter/example-model",
        messages=[{"role": "user", "content": "Inspect this project."}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "workspace.list",
                    "description": "List files",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        timeout_seconds=9,
    )

    assert result["choices"][0]["message"]["content"] == "Done"
    assert observed[0].url.path == "/v1/chat/completions"
    assert observed[0].headers["authorization"] == "Bearer tla_test_key"
    payload = json.loads(observed[0].content)
    assert payload["model"] == "openrouter/example-model"
    assert payload["tools"][0]["function"]["name"] == "workspace.list"
    assert payload["messages"][0]["content"] == "Inspect this project."


def test_gateway_client_loads_local_settings_from_environment(monkeypatch):
    monkeypatch.setenv("TOOLIXA_API_KEY", "tla_env_key")
    monkeypatch.setenv("TOOLIXA_MODEL", "local/qwen")
    monkeypatch.delenv("TOOLIXA_GATEWAY_URL", raising=False)

    client = GatewayChatClient.from_env()

    assert client.model == "local/qwen"
    assert client.base_url == "http://127.0.0.1:20128/v1"
    assert client.api_key == "tla_env_key"


def test_gateway_client_rejects_missing_gateway_key(monkeypatch):
    monkeypatch.delenv("TOOLIXA_API_KEY", raising=False)
    monkeypatch.setenv("TOOLIXA_MODEL", "local/qwen")

    with pytest.raises(ProviderError, match="TOOLIXA_API_KEY"):
        GatewayChatClient.from_env()


@pytest.mark.parametrize(
    "url",
    [
        "http://model-host.example/v1",
        "http://192.168.1.20:11434/v1",
        "http://user:password@127.0.0.1:20128/v1",
        "http://127.0.0.1:20128/v1?token=secret",
    ],
)
def test_gateway_client_rejects_untrusted_or_ambiguous_endpoint_urls(url):
    with pytest.raises(ProviderError):
        GatewayChatClient(url, "tla_test_key")


def test_gateway_error_does_not_echo_api_key():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key tla_sensitive_value"}})

    client = GatewayChatClient(
        "http://127.0.0.1:20128/v1",
        "tla_sensitive_value",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderError) as error:
        client.complete(
            model="local/qwen",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            timeout_seconds=2,
        )

    assert "tla_sensitive_value" not in str(error.value)
    assert "[REDACTED]" in str(error.value)
