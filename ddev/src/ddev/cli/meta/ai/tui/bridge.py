# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Bridge between the orchestrator callback system and the Textual message pump.

No widget or screen imports — this module only depends on callbacks and messages.
"""

from __future__ import annotations

from typing import Protocol

from textual.message import Message
from textual.message_pump import MessagePump

from ddev.ai.agent.scope import AgentScope
from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.callbacks.callbacks import CallbackSet
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult
from ddev.cli.meta.ai.tui.messages import (
    AfterCompact,
    AfterGoalCheck,
    AgentBeforeSend,
    AgentErrored,
    AgentFinished,
    AgentResponseReceived,
    AgentStarted,
    AgentToolCalled,
    BeforeCompact,
    BeforeGoalCheck,
    PhaseFinished,
    PhaseStarted,
)


class BridgeApp(Protocol):
    """App contract required by callback-to-message bridging."""

    bridge_target: MessagePump

    def post_message(self, message: Message) -> bool: ...


def build_app_callback_set(app: BridgeApp) -> CallbackSet:
    """Return a CallbackSet whose handlers post Textual messages to app.bridge_target.

    ``app.bridge_target`` is read on every callback invocation so the target can be
    changed at runtime (e.g. a screen registers itself after startup).

    The returned CallbackSet can be composed with others::

        app_set = build_app_callback_set(app)
        callbacks = Callbacks([app_set, *extra_sets])
    """
    cb = CallbackSet()

    def _target() -> MessagePump:
        return app.bridge_target

    @cb.on_phase_start
    async def _(phase_id: str) -> None:
        _target().post_message(PhaseStarted(phase_id))

    @cb.on_phase_finish
    async def _(phase_id: str) -> None:
        _target().post_message(PhaseFinished(phase_id))

    @cb.on_before_agent_send
    async def _(scope: AgentScope, prompt: str, iteration: int) -> None:
        _target().post_message(AgentBeforeSend(scope, prompt, iteration))

    @cb.on_agent_start
    async def _(scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
        _target().post_message(AgentStarted(scope, system_prompt, tools))

    @cb.on_agent_response
    async def _(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        _target().post_message(AgentResponseReceived(scope, response, iteration))

    @cb.on_tool_call
    async def _(scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        _target().post_message(AgentToolCalled(scope, tool_call, result, iteration))

    @cb.on_before_compact
    async def _(scope: AgentScope) -> None:
        _target().post_message(BeforeCompact(scope))

    @cb.on_after_compact
    async def _(scope: AgentScope) -> None:
        _target().post_message(AfterCompact(scope))

    @cb.on_agent_finish
    async def _(scope: AgentScope, result: ReActResult) -> None:
        _target().post_message(AgentFinished(scope, result))

    @cb.on_agent_error
    async def _(scope: AgentScope, error: BaseException) -> None:
        _target().post_message(AgentErrored(scope, error))

    @cb.on_before_goal_check
    async def _(phase_id: str, task_name: str, attempt: int) -> None:
        _target().post_message(BeforeGoalCheck(phase_id, task_name, attempt))

    @cb.on_after_goal_check
    async def _(phase_id: str, task_name: str, attempt: int, valid: bool, reason: str) -> None:
        _target().post_message(AfterGoalCheck(phase_id, task_name, attempt, valid, reason))

    return cb
