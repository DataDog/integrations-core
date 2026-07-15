# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.build import AgentRuntime, AgentRuntimeFactory
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.agents.spawn_subagent import SpawnSubagentTool
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from tests.ai.config.utils import make_agent_config


@pytest.fixture
def policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)


@pytest.fixture
def file_registry(policy) -> FileRegistry:
    return FileRegistry(policy=policy)


def test_runtime_factory_delegates_agent_building_and_builds_tools(file_registry):
    agent = MagicMock()
    provider = MagicMock()
    provider.build_agent.return_value = agent
    provider_registry = AgentProviderRegistry()
    provider_registry.register("custom", provider)
    factory = AgentRuntimeFactory(provider_registry=provider_registry, file_registry=file_registry)
    config = make_agent_config(provider="custom", tools=["read_file"])

    runtime = build_runtime(factory, config)

    assert runtime.agent is agent
    assert runtime.tool_registry.definitions[0]["name"] == "read_file"
    provider.build_agent.assert_called_once_with(
        config,
        tools=runtime.tool_registry,
        system_prompt="system",
        owner_id="p1",
    )


def make_factory(file_registry: FileRegistry) -> AgentRuntimeFactory:
    provider = MagicMock()
    provider.build_agent.return_value = MagicMock()
    provider_registry = AgentProviderRegistry()
    provider_registry.register("test", provider)
    return AgentRuntimeFactory(provider_registry=provider_registry, file_registry=file_registry)


# Opaque stand-in: build_runtime forwards it untouched and only the spawn tool stores it.
_PROCESS_FACTORY = object()


def build_runtime(
    factory: AgentRuntimeFactory,
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


def test_build_runtime_uses_config_tools(file_registry):
    config = make_agent_config(provider="test", tools=["read_file"])
    runtime = build_runtime(make_factory(file_registry), config)

    assert len(runtime.tool_registry.definitions) == 1
    assert runtime.tool_registry.definitions[0]["name"] == "read_file"


def test_build_runtime_wires_spawn_subagent_tool(file_registry):
    config = make_agent_config(provider="test", tools=["spawn_subagent"])
    factory = make_factory(file_registry)
    sentinel_process_factory = object()
    runtime = build_runtime(factory, config, process_factory=sentinel_process_factory)

    tool = runtime.tool_registry._tools["spawn_subagent"]
    assert isinstance(tool, SpawnSubagentTool)
    assert tool._agent_config is config
    assert tool._process_factory is sentinel_process_factory


def test_build_runtime_reuses_shared_file_registry(file_registry):
    config = make_agent_config(provider="test", tools=["read_file", "edit_file"])
    runtime = build_runtime(make_factory(file_registry), config, owner_id="owner")

    for tool in runtime.tool_registry._tools.values():
        assert tool._registry is file_registry
        assert tool._owner_id == "owner"


def test_build_runtime_native_tool_in_registry(file_registry):
    config = make_agent_config(provider="test", tools=["read_file", "web_search"])
    runtime = build_runtime(make_factory(file_registry), config)

    assert runtime.tool_registry.native_tool_names == ("web_search",)
    assert len(runtime.tool_registry.definitions) == 1
    assert runtime.tool_registry.definitions[0]["name"] == "read_file"


def test_build_runtime_no_native_tools_empty_list(file_registry):
    config = make_agent_config(provider="test", tools=["read_file"])
    runtime = build_runtime(make_factory(file_registry), config)

    assert runtime.tool_registry.native_tool_names == ()


async def test_shared_registry_does_not_share_parent_read_authorization(file_registry, tmp_path):
    config = make_agent_config(provider="test", tools=[])
    path = tmp_path / "file.txt"
    path.write_text("before", encoding="utf-8")
    file_registry.record("parent", str(path), "before")

    factory = make_factory(file_registry)
    child_config = config.model_copy(update={"tools": ["edit_file"]})
    runtime = build_runtime(factory, child_config, system_prompt="sys", owner_id="parent.sub.001-child")
    registry = runtime.tool_registry
    result = await registry.run("edit_file", {"path": str(path), "old_string": "before", "new_string": "after"})

    assert result.success is False
    assert "Not authorized" in result.error
    assert path.read_text(encoding="utf-8") == "before"
