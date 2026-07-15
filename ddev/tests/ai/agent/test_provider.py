# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

import ddev.ai.agent.provider as agent_provider
from ddev.ai.agent.provider import AnthropicProvider
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.config.utils import make_agent_config


def test_anthropic_client_is_created_lazily_and_cached(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    client_factory = MagicMock(return_value=client)
    monkeypatch.setattr(agent_provider.anthropic, "AsyncAnthropic", client_factory)
    provider = AnthropicProvider("secret")

    assert client_factory.call_count == 0
    assert provider.client is client
    assert provider.client is client
    client_factory.assert_called_once_with(api_key="secret")


def test_anthropic_provider_forwards_agent_configuration(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    monkeypatch.setattr(agent_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=client))
    agent_factory = MagicMock()
    monkeypatch.setattr(agent_provider, "AnthropicAgent", agent_factory)
    provider = AnthropicProvider("secret")
    tools = MagicMock(spec=ToolRegistry)
    config = make_agent_config(model="claude-opus-4-7", max_tokens=2048)

    provider.build_agent(config, tools=tools, system_prompt="system", owner_id="owner")

    agent_factory.assert_called_once_with(
        client=client,
        tools=tools,
        system_prompt="system",
        name="owner",
        model="claude-opus-4-7",
        max_tokens=2048,
    )
