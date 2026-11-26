# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from ddev.ai.agent.build import AgentRuntimeBuilder
from ddev.ai.agent.scope import AgentScope
from ddev.ai.config.models import AgentConfig
from ddev.ai.react.process import ReActProcess
from ddev.ai.run_events import RunEvents


class ReActProcessFactory:
    """Turns (scope, agent_config, system_prompt) into a scoped, runnable ReActProcess.

    Binds the run-wide `RunEvents` and a runtime builder once, so every caller
    creates processes the same way. Passes itself into the runtime builder so a
    ``spawn_subagent`` tool nested in the built runtime can launch children.
    """

    def __init__(self, runtime_builder: AgentRuntimeBuilder, events: RunEvents) -> None:
        self._runtime_builder = runtime_builder
        self._events = events

    def create(self, *, scope: AgentScope, agent_config: AgentConfig, system_prompt: str) -> ReActProcess:
        runtime = self._runtime_builder(
            agent_config=agent_config,
            system_prompt=system_prompt,
            process_factory=self,
            scope=scope,
        )
        return ReActProcess(runtime, events=self._events, scope=scope)
