# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Forward run events to the active Textual message target."""

from __future__ import annotations

from typing import Protocol

from textual.message import Message
from textual.message_pump import MessagePump

from ddev.ai.callbacks.callbacks import CallbackSet
from ddev.ai.react import notices
from ddev.ai.run_events import RunEvents
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
    ContextCleared,
    PhaseErrored,
    PhaseFinished,
    PhaseStarted,
    RunErrored,
)


class BridgeApp(Protocol):
    """App contract required by callback-to-message bridging."""

    bridge_target: MessagePump

    def post_message(self, message: Message) -> bool: ...


def build_app_callback_set(app: BridgeApp) -> CallbackSet:
    """Forward the remaining phase, goal-check and run callbacks."""
    cb = CallbackSet()

    def _target() -> MessagePump:
        return app.bridge_target

    @cb.on_phase_start
    async def _(phase_id: str) -> None:
        _target().post_message(PhaseStarted(phase_id))

    @cb.on_phase_finish
    async def _(phase_id: str) -> None:
        _target().post_message(PhaseFinished(phase_id))

    @cb.on_phase_error
    async def _(phase_id: str, error: BaseException) -> None:
        _target().post_message(PhaseErrored(phase_id, error))

    @cb.on_run_error
    async def _() -> None:
        _target().post_message(RunErrored())

    @cb.on_before_goal_check
    async def _(phase_id: str, task_name: str, attempt: int) -> None:
        _target().post_message(BeforeGoalCheck(phase_id, task_name, attempt))

    @cb.on_after_goal_check
    async def _(phase_id: str, task_name: str, attempt: int, valid: bool, reason: str) -> None:
        _target().post_message(AfterGoalCheck(phase_id, task_name, attempt, valid, reason))

    return cb


def subscribe_agent_notices(events: RunEvents, app: BridgeApp) -> None:
    async def before_agent_send(notice: notices.AgentBeforeSend) -> None:
        app.bridge_target.post_message(AgentBeforeSend(notice.scope, notice.prompt, notice.iteration))

    async def agent_start(notice: notices.AgentStarted) -> None:
        app.bridge_target.post_message(AgentStarted(notice.scope, notice.system_prompt, notice.tools))

    async def agent_response(notice: notices.AgentResponded) -> None:
        app.bridge_target.post_message(AgentResponseReceived(notice.scope, notice.response, notice.iteration))

    async def tool_call(notice: notices.ToolCalled) -> None:
        app.bridge_target.post_message(AgentToolCalled(notice.scope, notice.tool_call, notice.result, notice.iteration))

    async def before_compact(notice: notices.BeforeCompact) -> None:
        app.bridge_target.post_message(BeforeCompact(notice.scope))

    async def after_compact(notice: notices.AfterCompact) -> None:
        app.bridge_target.post_message(AfterCompact(notice.scope))

    async def context_cleared(notice: notices.ContextCleared) -> None:
        app.bridge_target.post_message(ContextCleared(notice.scope))

    async def agent_finish(notice: notices.AgentFinished) -> None:
        app.bridge_target.post_message(AgentFinished(notice.scope, notice.result))

    async def agent_error(notice: notices.AgentErrored) -> None:
        app.bridge_target.post_message(AgentErrored(notice.scope, notice.error))

    events.subscribe(notices.AgentBeforeSend, before_agent_send)
    events.subscribe(notices.AgentStarted, agent_start)
    events.subscribe(notices.AgentResponded, agent_response)
    events.subscribe(notices.ToolCalled, tool_call)
    events.subscribe(notices.BeforeCompact, before_compact)
    events.subscribe(notices.AfterCompact, after_compact)
    events.subscribe(notices.ContextCleared, context_cleared)
    events.subscribe(notices.AgentFinished, agent_finish)
    events.subscribe(notices.AgentErrored, agent_error)
