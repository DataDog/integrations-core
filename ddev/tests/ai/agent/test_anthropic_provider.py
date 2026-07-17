# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

import ddev.ai.agent.anthropic_provider as anthropic_provider
from ddev.ai.agent.anthropic_provider import DEFAULT_MODEL, MODEL_ALIASES, AnthropicProvider
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.config.utils import make_agent_config


def test_anthropic_client_is_created_lazily_and_cached(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    client_factory = MagicMock(return_value=client)
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", client_factory)
    provider = AnthropicProvider("secret")

    assert client_factory.call_count == 0
    assert provider.client is client
    assert provider.client is client
    client_factory.assert_called_once_with(api_key="secret")


@pytest.mark.parametrize("alias", sorted(MODEL_ALIASES))
def test_cast_model_resolves_each_alias(alias: str):
    provider = AnthropicProvider("secret")

    assert provider._cast_model(alias) == MODEL_ALIASES[alias]


@pytest.mark.parametrize("written", ["OPUS", "Opus", "oPuS"])
def test_cast_model_is_case_insensitive(written: str):
    provider = AnthropicProvider("secret")

    assert provider._cast_model(written) == MODEL_ALIASES["opus"]


def test_supported_models_are_the_aliases():
    provider = AnthropicProvider("secret")

    assert provider.supported_models() == frozenset(MODEL_ALIASES)


def test_cast_model_rejects_unknown_alias():
    provider = AnthropicProvider("secret")

    with pytest.raises(ValueError, match="Unknown model 'gpt'"):
        provider._cast_model("gpt")


def test_validate_config_rejects_unknown_model():
    provider = AnthropicProvider("secret")
    config = make_agent_config(model="bogus")

    with pytest.raises(ValueError, match="Unknown model 'bogus'"):
        provider.validate_config(config)


def test_validate_config_accepts_alias_and_unset_model():
    provider = AnthropicProvider("secret")

    provider.validate_config(make_agent_config(model="haiku"))
    provider.validate_config(make_agent_config())


def test_build_agent_forwards_agent_configuration(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=client))
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    provider = AnthropicProvider("secret")
    tools = MagicMock(spec=ToolRegistry)
    config = make_agent_config(model="opus", max_tokens=2048)

    provider.build_agent(config, tools=tools, system_prompt="system", owner_id="owner")

    agent_factory.assert_called_once_with(
        client=client,
        tools=tools,
        system_prompt="system",
        name="owner",
        model=MODEL_ALIASES["opus"],
        max_tokens=2048,
    )


def test_build_agent_uses_default_model_when_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=MagicMock()))
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    provider = AnthropicProvider("secret")

    provider.build_agent(make_agent_config(), tools=MagicMock(spec=ToolRegistry), system_prompt="s", owner_id="o")

    _, kwargs = agent_factory.call_args
    assert kwargs["model"] == MODEL_ALIASES[DEFAULT_MODEL]
    assert "max_tokens" not in kwargs
