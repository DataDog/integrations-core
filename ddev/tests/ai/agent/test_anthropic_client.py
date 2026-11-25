# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from unittest.mock import Mock

import httpx2
import pytest

from ddev.ai.agent.anthropic_client import SDK_AUTH_DISABLED, check_messages_access, messages_client
from ddev.ai.agent.exceptions import AgentConnectionError, ModelAccessError
from ddev.ai.errors import RunAbortError
from ddev.ai.model_catalog import ModelResolver, Route
from ddev.ai.runtime.connections import DirectConnection, GatewayConnection
from ddev.ai.runtime.tokens import DirectTokenProducer, TokenProducer


def _message(model: str) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
    )


@pytest.mark.parametrize("route", [Route.AI_GATEWAY, Route.DIRECT])
@pytest.mark.parametrize("use_env_key", [True, False], ids=["env-key", "profile"])
async def test_messages_only_sends_the_routes_credential(monkeypatch, tmp_path, route, use_env_key):
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "unrelated.json").write_text(
        json.dumps(
            {
                "base_url": "https://profile.example",
                "workspace_id": "other-workspace",
                "authentication": {"type": "user_oauth"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ANTHROPIC_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_PROFILE", "unrelated")
    if use_env_key:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "unrelated-env-key")
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "unrelated-env-token")
    else:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv(
        "ANTHROPIC_CUSTOM_HEADERS",
        "X-Api-Key: unrelated-key\nML-App-ID: other-app\nX-AI-Gateway-Provider: anthropic",
    )
    if route is Route.AI_GATEWAY:
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://override.example")
        expected_url = "https://ai-gateway.datadoghq.com/ai/v1/messages"
        wire_token = "ddpat_gateway_secret"
        expected_app = "togo"
    else:
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        expected_url = "https://api.anthropic.com/v1/messages"
        wire_token = "direct-secret"
        expected_app = None
    model = ModelResolver().resolve("haiku", route=route)

    def handle(request: httpx2.Request) -> httpx2.Response:
        assert request.url == expected_url
        credential_names = {"authorization", "x-api-key", "x-goog-api-key", "dd-api-key", "dd-application-key"}
        assert [(k, v) for k, v in request.headers.multi_items() if k in credential_names] == [
            ("authorization", f"Bearer {wire_token}")
        ]
        assert all(SDK_AUTH_DISABLED not in value for value in request.headers.values())
        assert "anthropic-workspace-id" not in request.headers
        assert "x-ai-gateway-provider" not in request.headers
        assert request.headers.get("ml-app-id") == expected_app
        assert json.loads(request.content)["model"] == model.binding.model
        assert wire_token.encode() not in request.content
        return _message(model.binding.model.removeprefix("anthropic/"))

    transport = httpx2.MockTransport(handle)
    if route is Route.AI_GATEWAY:
        tokens = Mock(spec=TokenProducer)
        tokens.token_for.return_value = wire_token
        connection = GatewayConnection(tokens, transport=transport)
    else:
        connection = DirectConnection(DirectTokenProducer({"anthropic": lambda: wire_token}), transport=transport)
    try:
        async with messages_client(connection) as client:
            assert client.api_key == SDK_AUTH_DISABLED
            assert client.auth_token is None
            assert client.credentials is None
            result = await check_messages_access(client, model)
    finally:
        await connection.aclose()

    assert result.status == 200
    assert result.model_confirmed


@pytest.mark.parametrize(
    ("transport_error", "expected_type", "expected_message"),
    [
        (RunAbortError("run cannot continue"), RunAbortError, "run cannot continue"),
        (ValueError("private diagnostic"), AgentConnectionError, "Model access check could not connect."),
    ],
    ids=["run-abort", "unknown-cause"],
)
async def test_access_probe_only_unwraps_known_transport_errors(transport_error, expected_type, expected_message):
    def fail(_: httpx2.Request) -> httpx2.Response:
        raise transport_error

    tokens = Mock(spec=TokenProducer)
    tokens.token_for.return_value = "ddpat_gateway_secret"
    connection = GatewayConnection(tokens, transport=httpx2.MockTransport(fail))
    model = ModelResolver().resolve("haiku", route=Route.AI_GATEWAY)
    try:
        async with messages_client(connection) as client:
            with pytest.raises(expected_type) as caught:
                await check_messages_access(client, model)
    finally:
        await connection.aclose()

    assert str(caught.value) == expected_message


@pytest.mark.parametrize(
    ("status", "message"), [(403, "Model access denied (HTTP 403)."), (400, "Model access check failed (HTTP 400).")]
)
async def test_messages_probe_reports_http_failure_without_response_body(status, message):
    transport = httpx2.MockTransport(lambda _: httpx2.Response(status, text="private diagnostic"))
    connection = DirectConnection(DirectTokenProducer({"anthropic": lambda: "direct-secret"}), transport=transport)
    model = ModelResolver().resolve("haiku", route=Route.DIRECT)
    try:
        async with messages_client(connection) as client:
            with pytest.raises(ModelAccessError) as caught:
                await check_messages_access(client, model)
    finally:
        await connection.aclose()

    assert caught.value.status_code == status
    assert str(caught.value) == message
