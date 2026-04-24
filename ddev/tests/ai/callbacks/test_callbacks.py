# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Shared argument fixtures
# ---------------------------------------------------------------------------

_RESPONSE = AgentResponse(
    stop_reason=StopReason.END_TURN,
    text="",
    tool_calls=[],
    usage=TokenUsage(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
)

_TOOL_CALL = ToolCall(id="tc_01", name="read_file", input={})

_TOOL_RESULT = ToolResult(success=True, data="ok")

_REACT_RESULT = ReActResult(
    final_response=_RESPONSE,
    iterations=1,
    total_input_tokens=10,
    total_output_tokens=5,
    context_usage=None,
)

_ERROR = RuntimeError("boom")

# ---------------------------------------------------------------------------
# Event table: (on_method_name, fire_method_name, fire_args)
# ---------------------------------------------------------------------------

EVENTS: list[tuple[str, str, tuple]] = [
    ("on_agent_response", "fire_agent_response", (_RESPONSE, 1)),
    ("on_tool_call", "fire_tool_call", (_TOOL_CALL, _TOOL_RESULT, 1)),
    ("on_complete", "fire_complete", (_REACT_RESULT,)),
    ("on_error", "fire_error", (_ERROR,)),
    ("on_before_compact", "fire_before_compact", ()),
    ("on_after_compact", "fire_after_compact", ()),
    ("on_before_agent_send", "fire_before_agent_send", (3,)),
    ("on_phase_start", "fire_phase_start", ("draft",)),
]

EVENT_IDS = [f"{on_name}" for on_name, _, _ in EVENTS]

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("on_name,_fire,_args", EVENTS, ids=EVENT_IDS)
async def test_decorator_returns_original_function(on_name: str, _fire: str, _args: tuple) -> None:
    cb = Callbacks()

    async def handler(*args: object) -> None:
        pass

    result = getattr(cb, on_name)(handler)
    assert result is handler


@pytest.mark.parametrize("on_name,fire_name,fire_args", EVENTS, ids=EVENT_IDS)
async def test_fire_dispatches_to_registered_handler_with_correct_args(
    on_name: str, fire_name: str, fire_args: tuple
) -> None:
    cb = Callbacks()
    received: list[tuple] = []

    async def handler(*args: object) -> None:
        received.append(args)

    getattr(cb, on_name)(handler)
    await getattr(cb, fire_name)(*fire_args)

    assert len(received) == 1
    for expected, actual in zip(fire_args, received[0], strict=False):
        assert actual is expected


async def test_handler_registered_on_one_event_not_fired_by_another() -> None:
    cb = Callbacks()
    invoked: list[bool] = []

    @cb.on_agent_response
    async def handler(response: object, iteration: int) -> None:
        invoked.append(True)

    await cb.fire_phase_start("p1")

    assert invoked == []


async def test_multiple_events_share_instance_without_interference() -> None:
    cb = Callbacks()
    agent_response_calls: list[tuple] = []
    phase_start_calls: list[str] = []

    @cb.on_agent_response
    async def on_response(response: object, iteration: int) -> None:
        agent_response_calls.append((response, iteration))

    @cb.on_phase_start
    async def on_start(phase_id: str) -> None:
        phase_start_calls.append(phase_id)

    await cb.fire_agent_response(_RESPONSE, 1)
    await cb.fire_phase_start("draft")

    assert len(agent_response_calls) == 1
    assert agent_response_calls[0][0] is _RESPONSE
    assert len(phase_start_calls) == 1
    assert phase_start_calls[0] == "draft"
