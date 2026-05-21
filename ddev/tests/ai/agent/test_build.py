# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.build import build_agent, make_agent_builder
from ddev.ai.phases.config import AgentConfig
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry


@pytest.fixture
def file_registry(tmp_path) -> FileRegistry:
    return FileRegistry(policy=FileAccessPolicy(write_root=tmp_path))


def test_build_agent_anthropic_returns_agent_and_registry(file_registry):
    agent_config = AgentConfig(provider="anthropic", model="claude-test", max_tokens=1024, tools=[])
    agent_clients = {"anthropic": MagicMock()}

    agent, registry = build_agent(
        agent_config=agent_config,
        agent_clients=agent_clients,
        system_prompt="hello",
        owner_id="p1",
        file_registry=file_registry,
    )

    assert isinstance(agent, AnthropicAgent)
    assert isinstance(registry, ToolRegistry)
    assert agent.name == "p1"


def test_build_agent_missing_client_raises(file_registry):
    agent_config = AgentConfig(provider="anthropic", tools=[])
    with pytest.raises(ValueError, match="No client provided for agent provider 'anthropic'"):
        build_agent(
            agent_config=agent_config,
            agent_clients={},
            system_prompt="hello",
            owner_id="p1",
            file_registry=file_registry,
        )


def test_build_agent_unknown_provider_raises(file_registry):
    agent_config = AgentConfig(provider="openai", tools=[])
    with pytest.raises(ValueError, match="Unknown agent provider: 'openai'"):
        build_agent(
            agent_config=agent_config,
            agent_clients={"openai": MagicMock()},
            system_prompt="hello",
            owner_id="p1",
            file_registry=file_registry,
        )


def test_make_agent_builder_returns_callable_that_delegates_to_build_agent(file_registry):
    agent_config = AgentConfig(provider="anthropic", tools=[])
    agent_clients = {"anthropic": MagicMock()}

    builder = make_agent_builder(
        agent_config=agent_config,
        agent_clients=agent_clients,
        file_registry=file_registry,
    )

    agent, registry = builder("system prompt", "p2")
    assert isinstance(agent, AnthropicAgent)
    assert isinstance(registry, ToolRegistry)
    assert agent.name == "p2"
