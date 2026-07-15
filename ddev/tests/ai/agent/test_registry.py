# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.registry import AgentProviderRegistry, build_agent_provider_registry
from ddev.ai.config.models import AgentConfig


def make_provider(*models: str) -> MagicMock:
    provider = MagicMock()
    provider.supported_models.return_value = frozenset(models)
    return provider


def test_registry_only_registers_configured_providers():
    without_key = build_agent_provider_registry(SimpleNamespace(anthropic_api_key=None))
    with_key = build_agent_provider_registry(SimpleNamespace(anthropic_api_key="secret"))

    assert not without_key.contains("anthropic")
    assert with_key.contains("anthropic")


def test_registry_rejects_duplicate_provider_registration():
    registry = AgentProviderRegistry()
    registry.register("custom", MagicMock())

    with pytest.raises(ValueError, match="already registered"):
        registry.register("custom", MagicMock())


def test_registry_rejects_unavailable_provider():
    registry = AgentProviderRegistry()
    config = AgentConfig.model_construct(provider="unknown")

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
