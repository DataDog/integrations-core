# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

import ddev.ai.agent.anthropic_provider as anthropic_provider
from ddev.ai.agent.anthropic_agent import DEFAULT_MAX_TOKENS
from ddev.ai.agent.anthropic_provider import (
    GATEWAY_EXECUTION_PENDING,
    AnthropicProvider,
)
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.models import AgentConfig
from ddev.ai.model_catalog import ANTHROPIC_MESSAGES, BindingConfig, ModelConfig, ModelResolver, Route
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.config.utils import make_agent_config

FIXTURE_WIRE_MODEL = "fixture-wire"


def make_resolver(
    tmp_path: Path, entry: ModelConfig, *, name: str = "fixture-model", aliases: dict[str, str] | None = None
) -> ModelResolver:
    data = {"models": {name: entry.model_dump(mode="json")}}
    if aliases:
        data["aliases"] = aliases
    path = tmp_path / "catalog.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return ModelResolver(path)


def make_entry(headers: dict[str, str] | None = None, max_output_tokens: int | None = None) -> ModelConfig:
    return ModelConfig(
        provider="anthropic",
        context_window=100_000,
        max_input_tokens=100_000,
        max_output_tokens=max_output_tokens,
        bindings={
            Route.DIRECT: BindingConfig(protocol=ANTHROPIC_MESSAGES, model=FIXTURE_WIRE_MODEL, headers=headers or {}),
            Route.AI_GATEWAY: BindingConfig(
                protocol=ANTHROPIC_MESSAGES, model=f"anthropic/{FIXTURE_WIRE_MODEL}", headers=headers or {}
            ),
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


def test_supported_models_include_canonical_names_and_aliases(tmp_path: Path):
    resolver = make_resolver(tmp_path, make_entry(), aliases={"fixture-alias": "fixture-model"})
    provider = AnthropicProvider("secret", resolver=resolver)

    models = provider.supported_models()

    assert models == frozenset({"fixture-model", "fixture-alias"})


def test_validate_config_rejects_unknown_model():
    provider = AnthropicProvider("secret")
    config = make_agent_config(model="bogus")

    with pytest.raises(ValueError, match="Unknown model 'bogus'"):
        provider.validate_config(config)


def test_validate_config_accepts_alias_and_canonical_names(tmp_path: Path):
    resolver = make_resolver(tmp_path, make_entry(), aliases={"fixture-alias": "fixture-model"})
    provider = AnthropicProvider("secret", resolver=resolver)

    provider.validate_config(make_agent_config(model="fixture-alias"))
    provider.validate_config(make_agent_config(model="fixture-model"))


@pytest.mark.parametrize("max_tokens", [None, 100_000], ids=["default", "explicit"])
def test_validate_config_rejects_max_tokens_above_the_declared_output_limit(tmp_path: Path, max_tokens: int | None):
    provider = AnthropicProvider("secret", resolver=make_resolver(tmp_path, make_entry(max_output_tokens=4096)))
    config = make_agent_config(model="fixture-model", max_tokens=max_tokens)

    requested = DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens
    with pytest.raises(ValueError, match=f"max_tokens {requested} exceeds the 4096-token output limit"):
        provider.validate_config(config)


def test_build_agent_forwards_agent_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    client = MagicMock()
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=client))
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    provider = AnthropicProvider("secret", resolver=make_resolver(tmp_path, make_entry()))
    tools = MagicMock(spec=ToolRegistry)
    config = make_agent_config(model="fixture-model", max_tokens=2048)

    provider.build_agent(config, tools=tools, system_prompt="system", owner_id="owner")

    kwargs = agent_factory.call_args.kwargs
    assert kwargs["model"].canonical == "fixture-model"
    assert kwargs["model"].binding.model == FIXTURE_WIRE_MODEL
    agent_factory.assert_called_once_with(
        client=client,
        tools=tools,
        system_prompt="system",
        name="owner",
        model=kwargs["model"],
        max_tokens=2048,
    )


def test_build_agent_uses_default_model_when_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(anthropic_provider, "DEFAULT_MODEL", "fixture-model")
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock(return_value=MagicMock()))
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    provider = AnthropicProvider("secret", resolver=make_resolver(tmp_path, make_entry()))
    registry = AgentProviderRegistry()
    registry.register("anthropic", provider)
    config = AgentConfig.model_validate({"provider": "anthropic"}, context={"provider_registry": registry})

    provider.build_agent(config, tools=MagicMock(spec=ToolRegistry), system_prompt="s", owner_id="o")

    kwargs = agent_factory.call_args.kwargs
    assert kwargs["model"].canonical == "fixture-model"
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


def test_gateway_build_agent_fails_before_any_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    client_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", client_factory)
    provider = AnthropicProvider(None, route=Route.AI_GATEWAY, resolver=make_resolver(tmp_path, make_entry()))

    with pytest.raises(ValueError, match=GATEWAY_EXECUTION_PENDING):
        provider.build_agent(
            make_agent_config(model="fixture-model"),
            tools=MagicMock(spec=ToolRegistry),
            system_prompt="s",
            owner_id="o",
        )

    client_factory.assert_not_called()


def test_gateway_mode_resolves_and_validates_models(tmp_path: Path):
    provider = AnthropicProvider(None, route=Route.AI_GATEWAY, resolver=make_resolver(tmp_path, make_entry()))

    resolved = provider.resolve_model("fixture-model")

    assert resolved.route is Route.AI_GATEWAY
    assert resolved.binding.model == f"anthropic/{FIXTURE_WIRE_MODEL}"
    provider.validate_config(make_agent_config(model="fixture-model"))
