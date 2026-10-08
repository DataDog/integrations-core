# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

import ddev.ai.agent.anthropic_provider as anthropic_provider
from ddev.ai.agent.anthropic_provider import (
    GATEWAY_EXECUTION_PENDING,
    AnthropicProvider,
)
from ddev.ai.model_catalog import ANTHROPIC_MESSAGES, BindingConfig, ModelConfig, ModelResolver, Route
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.config.utils import make_agent_config


def make_resolver(tmp_path: Path, entry: ModelConfig, name: str = "fixture-model") -> ModelResolver:
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml.safe_dump({"models": {name: entry.model_dump(mode="json")}}), encoding="utf-8")
    return ModelResolver(path)


def make_entry(headers: dict[str, str] | None = None, max_output_tokens: int | None = None) -> ModelConfig:
    return ModelConfig(
        provider="anthropic",
        context_window=100_000,
        max_input_tokens=100_000,
        max_output_tokens=max_output_tokens,
        bindings={
            Route.DIRECT: BindingConfig(protocol=ANTHROPIC_MESSAGES, model="fixture-model", headers=headers or {})
        },
    )


def test_anthropic_client_is_created_lazily_and_cached(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    client_factory = MagicMock(return_value=client)
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", client_factory)
    provider = AnthropicProvider("secret")

    assert client_factory.call_count == 0
    assert provider.client is client
    assert provider.client is client
    client_factory.assert_called_once_with(api_key="secret")


def test_client_construction_requires_an_api_key():
    provider = AnthropicProvider(None)

    with pytest.raises(ValueError, match="requires an API key"):
        _ = provider.client


def test_supported_models_include_canonical_names():
    provider = AnthropicProvider("secret")

    models = provider.supported_models()

    assert "claude-opus-5-5" in models
    assert "claude-sonnet-5-5" in models
    assert {"opus", "sonnet", "haiku"} <= models


def test_validate_config_rejects_unknown_model():
    provider = AnthropicProvider("secret")
    config = make_agent_config(model="bogus")

    with pytest.raises(ValueError, match="Unknown model 'bogus'"):
        provider.validate_config(config)


def test_validate_config_accepts_alias_and_unset_model():
    provider = AnthropicProvider("secret")

    provider.validate_config(make_agent_config(model="haiku"))
    provider.validate_config(make_agent_config())


def test_validate_config_rejects_max_tokens_above_the_output_limit():
    provider = AnthropicProvider("secret")
    config = make_agent_config(model="opus", max_tokens=200_000)

    with pytest.raises(ValueError, match="exceeds the 128000-token output limit of model 'claude-opus-5-5'"):
        provider.validate_config(config)


def test_validate_config_rejects_default_max_tokens_above_the_output_limit(tmp_path: Path):
    provider = AnthropicProvider("secret", resolver=make_resolver(tmp_path, make_entry(max_output_tokens=4096)))

    with pytest.raises(ValueError, match="max_tokens 8192 exceeds the 4096-token output limit"):
        provider.validate_config(make_agent_config(model="fixture-model"))


def test_build_agent_forwards_agent_configuration(monkeypatch: pytest.MonkeyPatch):
    client = MagicMock()
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=client))
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    provider = AnthropicProvider("secret")
    tools = MagicMock(spec=ToolRegistry)
    config = make_agent_config(model="opus", max_tokens=2048)

    provider.build_agent(config, tools=tools, system_prompt="system", owner_id="owner")

    kwargs = agent_factory.call_args.kwargs
    assert kwargs["model"].canonical == "claude-opus-5-5"
    assert kwargs["model"].binding.model == "claude-opus-5-5"
    assert kwargs["model"].model.context_window == 1_000_000
    agent_factory.assert_called_once_with(
        client=client,
        tools=tools,
        system_prompt="system",
        name="owner",
        model=kwargs["model"],
        max_tokens=2048,
    )


def test_build_agent_uses_default_model_when_unset(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=MagicMock()))
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    provider = AnthropicProvider("secret")

    provider.build_agent(make_agent_config(), tools=MagicMock(spec=ToolRegistry), system_prompt="s", owner_id="o")

    kwargs = agent_factory.call_args.kwargs
    assert kwargs["model"].canonical == "claude-sonnet-5"
    assert kwargs["model"].binding.model == "claude-sonnet-5"
    assert "max_tokens" not in kwargs


def test_build_agent_passes_binding_headers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=MagicMock()))
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    headers = {"anthropic-beta": "fixture-beta"}
    provider = AnthropicProvider("secret", resolver=make_resolver(tmp_path, make_entry(headers)))

    provider.build_agent(
        make_agent_config(model="fixture-model"), tools=MagicMock(spec=ToolRegistry), system_prompt="s", owner_id="a"
    )

    kwargs = agent_factory.call_args.kwargs
    assert kwargs["model"].binding.headers == headers


def test_gateway_build_agent_fails_before_any_request(monkeypatch: pytest.MonkeyPatch):
    client_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", client_factory)
    provider = AnthropicProvider(None, route=Route.AI_GATEWAY)

    with pytest.raises(ValueError, match=GATEWAY_EXECUTION_PENDING):
        provider.build_agent(
            make_agent_config(model="sonnet"), tools=MagicMock(spec=ToolRegistry), system_prompt="s", owner_id="o"
        )

    client_factory.assert_not_called()


def test_gateway_mode_resolves_and_validates_models():
    provider = AnthropicProvider(None, route=Route.AI_GATEWAY)

    resolved = provider.resolve_model("opus")

    assert resolved.route is Route.AI_GATEWAY
    assert resolved.binding.model == "anthropic/claude-opus-5-5"
    provider.validate_config(make_agent_config(model="claude-haiku-4-5"))
