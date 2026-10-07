# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

import ddev.ai.agent.anthropic_provider as anthropic_provider
from ddev.ai.agent.registry import AgentProviderRegistry, build_agent_provider_registry
from ddev.ai.config.models import AgentConfig
from tests.ai.config.utils import make_agent_config


def make_provider(*models: str) -> MagicMock:
    provider = MagicMock()
    provider.default_model.return_value = models[0] if models else "default-model"
    provider.supported_models.return_value = frozenset(models)
    return provider


def test_registry_only_registers_direct_providers_with_credentials():
    without_key = build_agent_provider_registry(
        SimpleNamespace(anthropic_api_key=None, use_ai_gateway=False, models_catalog=None)
    )
    with_key = build_agent_provider_registry(
        SimpleNamespace(anthropic_api_key="secret", use_ai_gateway=False, models_catalog=None)
    )

    assert not without_key.contains("anthropic")
    assert with_key.contains("anthropic")


def test_gateway_mode_registers_providers_without_direct_credentials():
    registry = build_agent_provider_registry(
        SimpleNamespace(anthropic_api_key=None, use_ai_gateway=True, models_catalog=None)
    )

    assert registry.contains("anthropic")
    config = AgentConfig.model_validate({"model": "claude-opus-5-5"}, context={"provider_registry": registry})
    assert config.provider == "anthropic"
    assert config.model == "claude-opus-5-5"


def test_registry_rejects_duplicate_provider_registration():
    registry = AgentProviderRegistry()
    registry.register("custom", MagicMock())

    with pytest.raises(ValueError, match="already registered"):
        registry.register("custom", MagicMock())


def test_registry_rejects_unavailable_provider():
    registry = AgentProviderRegistry()
    config = AgentConfig.model_construct(provider="unknown", model="claude-3-sonnet")

    with pytest.raises(ValueError, match="Agent provider 'unknown' is not available"):
        registry.validate_config(config)


def test_provider_for_model_resolves_unique_owner():
    registry = AgentProviderRegistry()
    registry.register("first", make_provider("model-a"))
    registry.register("second", make_provider("model-b"))

    assert registry.provider_for_model("model-a") == "first"
    assert registry.provider_for_model("model-b") == "second"


def test_provider_for_model_is_case_insensitive():
    registry = AgentProviderRegistry()
    registry.register("first", make_provider("Model-A"))

    assert registry.provider_for_model("model-a") == "first"


def test_registry_allows_shared_model_across_providers():
    registry = AgentProviderRegistry()
    registry.register("first", make_provider("shared"))
    registry.register("second", make_provider("shared"))

    assert registry.contains("first")
    assert registry.contains("second")


def test_provider_for_model_raises_only_when_ambiguous_model_is_resolved():
    registry = AgentProviderRegistry()
    registry.register("first", make_provider("shared", "only-first"))
    registry.register("second", make_provider("shared", "only-second"))

    assert registry.provider_for_model("only-first") == "first"
    assert registry.provider_for_model("only-second") == "second"

    with pytest.raises(ValueError, match="Model 'shared' is served by multiple providers"):
        registry.provider_for_model("shared")


def test_provider_for_model_rejects_unknown_model():
    registry = AgentProviderRegistry()
    registry.register("first", make_provider("model-a"))

    with pytest.raises(ValueError, match="Unknown model 'nope'"):
        registry.provider_for_model("nope")


def test_default_model_for_provider():
    registry = AgentProviderRegistry()
    registry.register("first", make_provider("model-a"))

    assert registry.default_model_for_provider("first") == "model-a"


def test_default_model_for_provider_rejects_unavailable_provider():
    registry = AgentProviderRegistry()

    with pytest.raises(ValueError, match="Agent provider 'unknown' is not available"):
        registry.default_model_for_provider("unknown")


def test_gateway_route_is_captured_when_the_registry_is_built():
    # A config edit after startup must not reroute agents built from this registry.
    config = SimpleNamespace(anthropic_api_key="secret", use_ai_gateway=True, models_catalog=None)
    registry = build_agent_provider_registry(config)
    config.use_ai_gateway = False

    with pytest.raises(ValueError, match="not implemented yet"):
        registry.build_agent(
            make_agent_config(model="sonnet"),
            tools=MagicMock(),
            system_prompt="system",
            owner_id="owner",
        )


CUSTOM_CATALOG = """\
models:
  fixture-model:
    provider: anthropic
    context_window: 100000
    bindings:
      direct:
        protocol: anthropic-messages
        model: Fixture-Wire
"""


def test_custom_catalog_is_captured_at_startup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    agent_factory = MagicMock()
    monkeypatch.setattr(anthropic_provider, "AnthropicAgent", agent_factory)
    monkeypatch.setattr(anthropic_provider.anthropic, "AsyncAnthropic", MagicMock())
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text(CUSTOM_CATALOG, encoding="utf-8")
    second.write_text(CUSTOM_CATALOG.replace("fixture-model", "other-model"), encoding="utf-8")
    config = SimpleNamespace(anthropic_api_key="secret", use_ai_gateway=False, models_catalog=str(first))
    registry = build_agent_provider_registry(config)

    # Later path or file edits must not reroute the registry built at startup.
    config.models_catalog = str(second)
    first.write_text(CUSTOM_CATALOG.replace("fixture-model", "rewired-model"), encoding="utf-8")

    context = {"provider_registry": registry}
    config = AgentConfig.model_validate({"model": "fixture-model"}, context=context)
    registry.build_agent(config, tools=MagicMock(), system_prompt="system", owner_id="owner")
    resolved = agent_factory.call_args.kwargs["model"]
    assert resolved.binding.model == "Fixture-Wire"
    assert resolved.model.context_window == 100_000
    for rejected in ("other-model", "rewired-model"):
        with pytest.raises(ValidationError, match="Unknown model"):
            AgentConfig.model_validate({"model": rejected}, context=context)
