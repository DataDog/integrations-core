# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Forward run events to the active Textual message target."""

from __future__ import annotations

from typing import Protocol

from textual.message import Message
from textual.message_pump import MessagePump

from ddev.ai.phases import notices as phase_notices
from ddev.ai.react import notices
from ddev.ai.run_events import RunEvents
from ddev.ai.runtime.notices import RunErrored as RunErroredNotice
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
    """App contract required by forwarding notices to Textual."""

    bridge_target: MessagePump

    def post_message(self, message: Message) -> bool: ...


def subscribe_run_notices(events: RunEvents, app: BridgeApp) -> None:
    async def phase_start(notice: phase_notices.PhaseStarted) -> None:
        app.bridge_target.post_message(PhaseStarted(notice.phase_id))

    async def phase_finish(notice: phase_notices.PhaseFinished) -> None:
        app.bridge_target.post_message(PhaseFinished(notice.phase_id))

    async def phase_error(notice: phase_notices.PhaseErrored) -> None:
        app.bridge_target.post_message(PhaseErrored(notice.phase_id, notice.error))

    async def run_error(notice: RunErroredNotice) -> None:
        app.bridge_target.post_message(RunErrored())

    async def before_goal_check(notice: phase_notices.BeforeGoalCheck) -> None:
        app.bridge_target.post_message(BeforeGoalCheck(notice.phase_id, notice.task_name, notice.attempt))

    async def after_goal_check(notice: phase_notices.AfterGoalCheck) -> None:
        app.bridge_target.post_message(
            AfterGoalCheck(notice.phase_id, notice.task_name, notice.attempt, notice.valid, notice.reason)
        )

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

    events.subscribe(phase_notices.PhaseStarted, phase_start)
    events.subscribe(phase_notices.PhaseFinished, phase_finish)
    events.subscribe(phase_notices.PhaseErrored, phase_error)
    events.subscribe(RunErroredNotice, run_error)
    events.subscribe(phase_notices.BeforeGoalCheck, before_goal_check)
    events.subscribe(phase_notices.AfterGoalCheck, after_goal_check)
    events.subscribe(notices.AgentBeforeSend, before_agent_send)
    events.subscribe(notices.AgentStarted, agent_start)
    events.subscribe(notices.AgentResponded, agent_response)
    events.subscribe(notices.ToolCalled, tool_call)
    events.subscribe(notices.BeforeCompact, before_compact)
    events.subscribe(notices.AfterCompact, after_compact)
    events.subscribe(notices.ContextCleared, context_cleared)
    events.subscribe(notices.AgentFinished, agent_finish)
    events.subscribe(notices.AgentErrored, agent_error)
