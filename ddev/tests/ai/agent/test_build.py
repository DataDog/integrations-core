# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.build import AgentRuntime, DefaultAgentRuntimeFactory
from ddev.ai.phases.config import AgentConfig
from ddev.ai.tools.agents.spawn_subagent import SpawnSubagentTool
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


def make_factory(
    clients: dict,
    file_registry: FileRegistry,
) -> DefaultAgentRuntimeFactory:
    return DefaultAgentRuntimeFactory(
        agent_clients=clients,
        file_registry=file_registry,
    )


# Opaque stand-in: build_runtime forwards it untouched and only the spawn tool stores it.
_PROCESS_FACTORY = object()


def build_runtime(
    factory: DefaultAgentRuntimeFactory,
    config: AgentConfig,
    *,
    system_prompt: str = "system",
    owner_id: str = "p1",
    process_factory: object = _PROCESS_FACTORY,
) -> AgentRuntime:
    return factory.build_runtime(
        agent_config=config,
        system_prompt=system_prompt,
        owner_id=owner_id,
        process_factory=process_factory,
    )


def test_unknown_provider_raises(file_registry, clients):
    config = AgentConfig.model_construct(provider="bad_provider", tools=[])
    factory = make_factory(clients, file_registry)
    with pytest.raises(ValueError, match="Unknown agent provider: 'bad_provider'"):
        build_runtime(factory, config)


def test_missing_client_raises(file_registry):
    config = AgentConfig(provider="anthropic", tools=[])
    factory = make_factory({}, file_registry)
    with pytest.raises(ValueError, match="No client provided for agent provider 'anthropic'"):
        build_runtime(factory, config)


def test_build_runtime_returns_agent_runtime(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=[])
    runtime = build_runtime(make_factory(clients, file_registry), config)

    assert isinstance(runtime, AgentRuntime)
    assert isinstance(runtime.agent, AnthropicAgent)
    assert isinstance(runtime.tool_registry, ToolRegistry)
    assert runtime.agent.name == "p1"


def test_build_runtime_uses_explicit_system_prompt(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=[])
    runtime = build_runtime(make_factory(clients, file_registry), config, system_prompt="Project: integrations")

    assert runtime.agent._system_prompt == "Project: integrations"


@pytest.mark.parametrize(
    "model,max_tokens",
    [
        ("claude-opus-4-7", 2048),
        ("claude-haiku-4-5", 512),
    ],
)
def test_build_runtime_forwards_model_and_max_tokens(file_registry, clients, model, max_tokens):
    config = AgentConfig(provider="anthropic", model=model, max_tokens=max_tokens, tools=[])
    runtime = build_runtime(make_factory(clients, file_registry), config)

    assert runtime.agent._model == model
    assert runtime.agent._max_tokens == max_tokens


def test_build_runtime_uses_config_tools(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=["read_file"])
    runtime = build_runtime(make_factory(clients, file_registry), config)

    assert len(runtime.tool_registry.definitions) == 1
    assert runtime.tool_registry.definitions[0]["name"] == "read_file"


def test_build_runtime_wires_spawn_subagent_tool(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=["spawn_subagent"])
    factory = make_factory(clients, file_registry)
    sentinel_process_factory = object()
    runtime = build_runtime(factory, config, process_factory=sentinel_process_factory)

    tool = runtime.tool_registry._tools["spawn_subagent"]
    assert isinstance(tool, SpawnSubagentTool)
    assert tool._agent_config is config
    assert tool._process_factory is sentinel_process_factory


def test_build_runtime_reuses_shared_file_registry(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=["read_file", "edit_file"])
    runtime = build_runtime(make_factory(clients, file_registry), config, owner_id="owner")

    for tool in runtime.tool_registry._tools.values():
        assert tool._registry is file_registry
        assert tool._owner_id == "owner"


def test_build_runtime_native_tool_in_registry(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=["read_file", "web_search"])
    runtime = build_runtime(make_factory(clients, file_registry), config)

    assert list(runtime.tool_registry.native_tool_names) == ["web_search"]
    assert len(runtime.tool_registry.definitions) == 1
    assert runtime.tool_registry.definitions[0]["name"] == "read_file"


def test_build_runtime_no_native_tools_empty_list(file_registry, clients):
    config = AgentConfig(provider="anthropic", tools=["read_file"])
    runtime = build_runtime(make_factory(clients, file_registry), config)

    assert list(runtime.tool_registry.native_tool_names) == []


async def test_shared_registry_does_not_share_parent_read_authorization(file_registry, clients, tmp_path):
    config = AgentConfig(provider="anthropic", tools=[])
    path = tmp_path / "file.txt"
    path.write_text("before", encoding="utf-8")
    file_registry.record("parent", str(path), "before")

    factory = make_factory(clients, file_registry)
    child_config = config.model_copy(update={"tools": ["edit_file"]})
    runtime = build_runtime(factory, child_config, system_prompt="sys", owner_id="parent.sub.001-child")
    registry = runtime.tool_registry
    result = await registry.run("edit_file", {"path": str(path), "old_string": "before", "new_string": "after"})

    assert result.success is False
    assert "Not authorized" in result.error
    assert path.read_text(encoding="utf-8") == "before"
