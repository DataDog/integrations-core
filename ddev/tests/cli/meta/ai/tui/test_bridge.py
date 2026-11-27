# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Run events reach the Textual message target with their payloads."""

from __future__ import annotations

import pytest

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import AgentResponse as AgentResponsePayload
from ddev.ai.agent.types import StopReason, TokenUsage, ToolCall
from ddev.ai.phases import notices as phase_notices
from ddev.ai.react import notices
from ddev.ai.react.types import ReActResult
from ddev.ai.run_events import RunEvents
from ddev.ai.runtime.notices import RunErrored as RunErroredNotice
from ddev.ai.tools.core.types import ToolResult
from ddev.cli.meta.ai.tui.bridge import subscribe_run_notices
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

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SCOPE = AgentScope(owner_id="test_agent", role=AgentRole.PHASE, phase_id="test_agent")


def _make_response() -> AgentResponsePayload:
    usage = TokenUsage(
        input_tokens=10,
        output_tokens=5,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return AgentResponsePayload(
        stop_reason=StopReason.END_TURN,
        text="hello",
        tool_calls=[],
        usage=usage,
    )


def _make_react_result() -> ReActResult:
    return ReActResult(
        final_response=_make_response(),
        iterations=3,
        total_input_tokens=30,
        total_output_tokens=15,
        context_usage=None,
    )


class StubOrchestrator:
    def __init__(self, events: RunEvents) -> None:
        self.events = events

    async def run_async(self) -> None:
        tool_call = ToolCall(id="tc1", name="bash", input={"cmd": "ls"})
        result = ToolResult(success=True, data="file.txt")

        await self.events.notify(phase_notices.PhaseStarted("phase1"))
        await self.events.notify(phase_notices.PhaseFinished("phase1"))
        await self.events.notify(phase_notices.PhaseErrored("phase1", ValueError("phase boom")))
        await self.events.notify(RunErroredNotice())
        await self.events.notify(notices.AgentStarted(SCOPE, "sys_prompt", ["bash", "python"]))
        await self.events.notify(notices.AgentResponded(SCOPE, _make_response(), 1))
        await self.events.notify(notices.ToolCalled(SCOPE, tool_call, result, 1))
        await self.events.notify(notices.BeforeCompact(SCOPE))
        await self.events.notify(notices.AfterCompact(SCOPE))
        await self.events.notify(notices.ContextCleared(SCOPE))
        await self.events.notify(notices.AgentFinished(SCOPE, _make_react_result()))
        await self.events.notify(notices.AgentErrored(SCOPE, ValueError("boom")))
        await self.events.notify(phase_notices.BeforeGoalCheck("phase1", "task1", 1))
        await self.events.notify(phase_notices.AfterGoalCheck("phase1", "task1", 1, True, "looks good"))


# ---------------------------------------------------------------------------
# Shared fixture: run StubOrchestrator once and expose app.received
# ---------------------------------------------------------------------------


@pytest.fixture
async def received_from_stub(make_togo_app):
    """Run StubOrchestrator once and return the full app.received list."""
    app = make_togo_app([])
    async with app.run_test() as pilot:
        events = RunEvents()
        subscribe_run_notices(events, app)
        stub = StubOrchestrator(events)
        app.run_flow(stub)
        await pilot.pause(0.3)
    return app.received


# ---------------------------------------------------------------------------
# Bridge → app sink: each event type delivers the right message
# ---------------------------------------------------------------------------


async def test_phase_started_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, PhaseStarted)]
    assert len(msgs) == 1
    assert msgs[0].phase_id == "phase1"


async def test_phase_finished_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, PhaseFinished)]
    assert len(msgs) == 1
    assert msgs[0].phase_id == "phase1"


async def test_phase_errored_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, PhaseErrored)]
    assert len(msgs) == 1
    assert msgs[0].phase_id == "phase1"
    assert str(msgs[0].error) == "phase boom"


async def test_run_errored_signal(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, RunErrored)]
    assert len(msgs) == 1


async def test_agent_started_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, AgentStarted)]
    assert len(msgs) == 1
    assert msgs[0].scope.owner_id == "test_agent"
    assert msgs[0].system_prompt == "sys_prompt"
    assert msgs[0].tools == ["bash", "python"]


async def test_agent_response_received_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, AgentResponseReceived)]
    assert len(msgs) == 1
    assert msgs[0].response.text == "hello"
    assert msgs[0].iteration == 1
    assert msgs[0].scope is SCOPE


async def test_agent_tool_called_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, AgentToolCalled)]
    assert len(msgs) == 1
    assert msgs[0].tool_call.name == "bash"
    assert msgs[0].result.data == "file.txt"
    assert msgs[0].iteration == 1


async def test_before_compact_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, BeforeCompact)]
    assert len(msgs) == 1
    assert msgs[0].scope is SCOPE


async def test_after_compact_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, AfterCompact)]
    assert len(msgs) == 1
    assert msgs[0].scope is SCOPE


async def test_context_cleared_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, ContextCleared)]
    assert len(msgs) == 1
    assert msgs[0].scope is SCOPE


async def test_agent_finished_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, AgentFinished)]
    assert len(msgs) == 1
    assert msgs[0].result.iterations == 3
    assert msgs[0].scope is SCOPE


async def test_agent_errored_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, AgentErrored)]
    assert len(msgs) == 1
    assert isinstance(msgs[0].error, ValueError)
    assert str(msgs[0].error) == "boom"


async def test_before_goal_check_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, BeforeGoalCheck)]
    assert len(msgs) == 1
    assert msgs[0].phase_id == "phase1"
    assert msgs[0].task_name == "task1"
    assert msgs[0].attempt == 1


async def test_after_goal_check_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, AfterGoalCheck)]
    assert len(msgs) == 1
    assert msgs[0].phase_id == "phase1"
    assert msgs[0].task_name == "task1"
    assert msgs[0].attempt == 1
    assert msgs[0].valid is True
    assert msgs[0].reason == "looks good"


async def test_all_14_messages_delivered(make_togo_app):
    """Every bridge event type delivers exactly one message to the sink."""
    app = make_togo_app([])
    async with app.run_test() as pilot:
        events = RunEvents()
        subscribe_run_notices(events, app)
        stub = StubOrchestrator(events)
        app.run_flow(stub)
        await pilot.pause(0.3)

    assert len(app.received) == 14


# ---------------------------------------------------------------------------
# AgentBeforeSend: new bridge event for on_before_agent_send
# ---------------------------------------------------------------------------


async def test_agent_before_send_non_sentinel_delivered(make_togo_app):
    """AgentBeforeSend is posted when the prompt is not TOOL_RESULTS_SENTINEL."""
    app = make_togo_app([])
    async with app.run_test() as pilot:
        events = RunEvents()
        subscribe_run_notices(events, app)
        await events.notify(notices.AgentBeforeSend(SCOPE, "Analyze the metrics.", 1))
        await pilot.pause(0.2)

    msgs = [m for m in app.received if isinstance(m, AgentBeforeSend)]
    assert len(msgs) == 1
    assert msgs[0].scope is SCOPE
    assert msgs[0].prompt == "Analyze the metrics."
    assert msgs[0].iteration == 1


async def test_agent_before_send_sentinel_delivered(make_togo_app):
    """AgentBeforeSend is posted for tool-result sends so the TUI can show thinking state."""
    from ddev.ai.react.process import TOOL_RESULTS_SENTINEL

    app = make_togo_app([])
    async with app.run_test() as pilot:
        events = RunEvents()
        subscribe_run_notices(events, app)
        await events.notify(notices.AgentBeforeSend(SCOPE, TOOL_RESULTS_SENTINEL, 2))
        await pilot.pause(0.2)

    msgs = [m for m in app.received if isinstance(m, AgentBeforeSend)]
    assert len(msgs) == 1
    assert msgs[0].scope is SCOPE
    assert msgs[0].prompt == TOOL_RESULTS_SENTINEL
    assert msgs[0].iteration == 2


async def test_agent_before_send_payload_scope_and_iteration(make_togo_app):
    """AgentBeforeSend carries the correct scope, prompt, and iteration."""
    from ddev.ai.agent.scope import AgentRole, AgentScope

    scope = AgentScope(owner_id="phase_x", role=AgentRole.SUBAGENT, phase_id="phase_x")

    app = make_togo_app([])
    async with app.run_test() as pilot:
        events = RunEvents()
        subscribe_run_notices(events, app)
        await events.notify(notices.AgentBeforeSend(scope, "Inspect the endpoint.", 3))
        await pilot.pause(0.2)

    msgs = [m for m in app.received if isinstance(m, AgentBeforeSend)]
    assert len(msgs) == 1
    assert msgs[0].scope.owner_id == "phase_x"
    assert msgs[0].scope.role.value == "subagent"
    assert msgs[0].prompt == "Inspect the endpoint."
    assert msgs[0].iteration == 3
