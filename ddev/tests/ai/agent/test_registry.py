# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.registry import AgentProviderRegistry, build_agent_provider_registry
from ddev.ai.config.models import AgentConfig


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


def test_registry_validates_config_before_building_agent():
    provider = MagicMock()
    provider.validate_config.side_effect = ValueError("config rejected")
    registry = AgentProviderRegistry()
    registry.register("custom", provider)
    config = AgentConfig.model_construct(provider="custom")

    with pytest.raises(ValueError, match="config rejected"):
        registry.build_agent(config, tools=MagicMock(), system_prompt="system", owner_id="owner")

    provider.build_agent.assert_not_called()
