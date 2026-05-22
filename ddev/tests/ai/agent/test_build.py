# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.build import build_agent, build_subagent, make_agent_builder, make_subagent_builder
from ddev.ai.phases.config import AgentConfig
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry


@pytest.fixture
def policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)


@pytest.fixture
def file_registry(policy) -> FileRegistry:
    return FileRegistry(policy=policy)


@pytest.fixture
def clients() -> dict:
    return {"anthropic": MagicMock()}


# ---------------------------------------------------------------------------
# Core builder behaviour
# ---------------------------------------------------------------------------


def test_unknown_provider_raises(file_registry, clients):
    config = AgentConfig.model_construct(provider="bad_provider", tools=[])
    with pytest.raises(ValueError, match="Unknown agent provider: 'bad_provider'"):
        build_agent(config, clients, "sys", "p1", file_registry)


def test_missing_client_raises(file_registry):
    config = AgentConfig(provider="anthropic", tools=[])
    with pytest.raises(ValueError, match="No client provided for agent provider 'anthropic'"):
        build_agent(config, {}, "sys", "p1", file_registry)


def test_builds_anthropic_agent_with_correct_types_and_name(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=[])
    agent, registry = build_agent(config, clients, "sys", "p1", file_registry)
    assert isinstance(agent, AnthropicAgent)
    assert isinstance(registry, ToolRegistry)
    assert agent.name == "p1"


@pytest.mark.parametrize(
    "model,max_tokens",
    [
        ("claude-opus-4-7", 2048),
        ("claude-haiku-4-5", 512),
    ],
)
def test_model_and_max_tokens_forwarded(file_registry, clients, model, max_tokens):
    config = AgentConfig(provider="anthropic", model=model, max_tokens=max_tokens, tools=[])
    agent, _ = build_agent(config, clients, "sys", "p1", file_registry)
    assert agent._model == model
    assert agent._max_tokens == max_tokens


def test_build_agent_uses_config_tools(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=["read_file"])
    _, registry = build_agent(config, clients, "sys", "p1", file_registry)
    assert len(registry.definitions) == 1
    assert registry.definitions[0]["name"] == "read_file"


# ---------------------------------------------------------------------------
# build_subagent
# ---------------------------------------------------------------------------


def test_build_subagent_reuses_shared_file_registry(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=[])
    _, registry = build_subagent(config, clients, file_registry, "sys", "child", ["read_file", "edit_file"])

    for tool in registry._tools.values():
        assert tool._registry is file_registry
        assert tool._owner_id == "child"


def test_build_subagent_recursion_guard(file_registry, clients):
    config = AgentConfig.model_construct(provider="anthropic", tools=[])
    with pytest.raises(ValueError):
        build_subagent(config, clients, file_registry, "sys", "sub", ["spawn_subagent"])


async def test_shared_registry_does_not_share_parent_read_authorization(file_registry, clients, tmp_path):
    config = AgentConfig(provider="anthropic", tools=[])
    path = tmp_path / "file.txt"
    path.write_text("before", encoding="utf-8")
    file_registry.record("parent", str(path), "before")

    _, registry = build_subagent(config, clients, file_registry, "sys", "parent.sub.001-child", ["edit_file"])
    result = await registry.run("edit_file", {"path": str(path), "old_string": "before", "new_string": "after"})

    assert result.success is False
    assert "Not authorized" in result.error
    assert path.read_text(encoding="utf-8") == "before"


# ---------------------------------------------------------------------------
# Closures — verify delegation works and signatures are correct
# ---------------------------------------------------------------------------


def test_make_agent_builder(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=[])
    builder = make_agent_builder(config, clients, file_registry)
    agent, registry = builder("sys", "p1", None, None)
    assert isinstance(agent, AnthropicAgent)
    assert agent.name == "p1"


def test_make_subagent_builder(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=[])
    builder = make_subagent_builder(config, clients, file_registry)
    agent, registry = builder("sys", "sub-1", [])
    assert isinstance(agent, AnthropicAgent)
    assert agent.name == "sub-1"
