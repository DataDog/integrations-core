# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import AgentResponse, ToolResultMessage
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.react.factory import ReActProcessFactory
from ddev.ai.react.process import ReActProcess
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.config.utils import make_agent_config


class _StubAgent(BaseAgent[Any]):
    def __init__(self, name: str) -> None:
        super().__init__(name=name, system_prompt="", tools=ToolRegistry([]))

    async def send(
        self, content: str | list[ToolResultMessage], allowed_tools: list[str] | None = None
    ) -> AgentResponse:
        raise AssertionError("send should not be called")


def test_create_returns_scoped_process_and_forwards_build_inputs():
    calls: list[dict] = []

    def runtime_builder(*, agent_config, system_prompt, process_factory, scope):
        calls.append(
            {
                "agent_config": agent_config,
                "system_prompt": system_prompt,
                "process_factory": process_factory,
                "scope": scope,
            }
        )
        return AgentRuntime(agent=_StubAgent(scope.owner_id), tool_registry=ToolRegistry([]))

    callbacks = Callbacks([CallbackSet()])
    factory = ReActProcessFactory(runtime_builder, callbacks)

    scope = AgentScope(owner_id="p1.sub.001-x", role=AgentRole.SUBAGENT, phase_id="p1")
    config = make_agent_config(tools=["read_file"])
    process = factory.create(scope=scope, agent_config=config, system_prompt="be helpful")

    assert isinstance(process, ReActProcess)
    assert process._scope is scope
    assert process._callbacks is callbacks

    assert len(calls) == 1
    assert calls[0]["scope"] is scope
    assert calls[0]["agent_config"] is config
    assert calls[0]["system_prompt"] == "be helpful"
    # The factory injects itself so nested spawn tools can create children.
    assert calls[0]["process_factory"] is factory
