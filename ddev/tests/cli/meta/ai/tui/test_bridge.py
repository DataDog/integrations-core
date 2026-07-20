# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for tui/bridge.py: build_app_callback_set delivers the right Textual messages."""

from __future__ import annotations

import pytest

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import AgentResponse as AgentResponsePayload
from ddev.ai.agent.types import StopReason, TokenUsage, ToolCall
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult
from ddev.cli.meta.ai.tui.bridge import build_app_callback_set
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
    """Fires one of every callback event so each bridge handler is exercised exactly once."""

    def __init__(self, cb_set: CallbackSet) -> None:
        self.cb_set = cb_set

    async def run_async(self) -> None:
        tool_call = ToolCall(id="tc1", name="bash", input={"cmd": "ls"})
        result = ToolResult(success=True, data="file.txt")

        await self.cb_set.fire_phase_start("phase1")
        await self.cb_set.fire_phase_finish("phase1")
        await self.cb_set.fire_phase_error("phase1", ValueError("phase boom"))
        await self.cb_set.fire_run_error(RuntimeError("run boom"), "phase1")
        await self.cb_set.fire_agent_start(SCOPE, "sys_prompt", ["bash", "python"])
        await self.cb_set.fire_agent_response(SCOPE, _make_response(), 1)
        await self.cb_set.fire_tool_call(SCOPE, tool_call, result, 1)
        await self.cb_set.fire_before_compact(SCOPE)
        await self.cb_set.fire_after_compact(SCOPE)
        await self.cb_set.fire_context_cleared(SCOPE)
        await self.cb_set.fire_agent_finish(SCOPE, _make_react_result())
        await self.cb_set.fire_agent_error(SCOPE, ValueError("boom"))
        await self.cb_set.fire_before_goal_check("phase1", "task1", 1)
        await self.cb_set.fire_after_goal_check("phase1", "task1", 1, True, "looks good")


# ---------------------------------------------------------------------------
# Factory: type, composition, and basic wiring
# ---------------------------------------------------------------------------


async def test_build_app_callback_set_wires_correctly(make_togo_app):
    """build_app_callback_set returns a wired CallbackSet that routes events to the app sink."""
    app = make_togo_app([])
    async with app.run_test() as pilot:
        cb = build_app_callback_set(app)
        assert isinstance(cb, CallbackSet)
        combined = Callbacks([cb])
        assert isinstance(combined, Callbacks)
        # Fire one real event to confirm the wiring delivers a message
        await combined.fire_phase_start("wiring_phase")
        await pilot.pause(0.1)
    phase_started = [m for m in app.received if isinstance(m, PhaseStarted)]
    assert len(phase_started) == 1
    assert phase_started[0].phase_id == "wiring_phase"


# ---------------------------------------------------------------------------
# Shared fixture: run StubOrchestrator once and expose app.received
# ---------------------------------------------------------------------------


@pytest.fixture
async def received_from_stub(make_togo_app):
    """Run StubOrchestrator once and return the full app.received list."""
    app = make_togo_app([])
    async with app.run_test() as pilot:
        cb = build_app_callback_set(app)
        stub = StubOrchestrator(cb)
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


async def test_run_errored_payload(received_from_stub):
    msgs = [m for m in received_from_stub if isinstance(m, RunErrored)]
    assert len(msgs) == 1
    assert msgs[0].phase_id == "phase1"
    assert str(msgs[0].error) == "run boom"


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
        cb = build_app_callback_set(app)
        stub = StubOrchestrator(cb)
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
        cb = build_app_callback_set(app)
        combined = Callbacks([cb])
        await combined.fire_before_agent_send(SCOPE, "Analyze the metrics.", 1)
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
        cb = build_app_callback_set(app)
        combined = Callbacks([cb])
        await combined.fire_before_agent_send(SCOPE, TOOL_RESULTS_SENTINEL, 2)
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
        cb = build_app_callback_set(app)
        combined = Callbacks([cb])
        await combined.fire_before_agent_send(scope, "Inspect the endpoint.", 3)
        await pilot.pause(0.2)

    msgs = [m for m in app.received if isinstance(m, AgentBeforeSend)]
    assert len(msgs) == 1
    assert msgs[0].scope.owner_id == "phase_x"
    assert msgs[0].scope.role.value == "subagent"
    assert msgs[0].prompt == "Inspect the endpoint."
    assert msgs[0].iteration == 3
