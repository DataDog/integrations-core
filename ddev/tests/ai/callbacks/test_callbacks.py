# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
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
    ("on_phase_finish", "fire_phase_finish", ("draft",)),
]

EVENT_IDS = [on_name for on_name, _, _ in EVENTS]

# ===========================================================================
# CallbackSet tests
# ===========================================================================


@pytest.mark.parametrize("on_name,_fire,_args", EVENTS, ids=EVENT_IDS)
async def test_decorator_returns_original_function(on_name: str, _fire: str, _args: tuple) -> None:
    cb = CallbackSet()

    async def handler(*args: object) -> None:
        pass

    result = getattr(cb, on_name)(handler)
    assert result is handler


@pytest.mark.parametrize("on_name,fire_name,fire_args", EVENTS, ids=EVENT_IDS)
async def test_fire_dispatches_to_registered_handler_with_correct_args(
    on_name: str, fire_name: str, fire_args: tuple
) -> None:
    cb = CallbackSet()
    received: list[tuple] = []

    async def handler(*args: object) -> None:
        received.append(args)

    getattr(cb, on_name)(handler)
    await getattr(cb, fire_name)(*fire_args)

    assert len(received) == 1
    for expected, actual in zip(fire_args, received[0], strict=False):
        assert actual is expected


@pytest.mark.parametrize("on_name,fire_name,fire_args", EVENTS, ids=EVENT_IDS)
async def test_empty_callback_set_fire_is_noop(on_name: str, fire_name: str, fire_args: tuple) -> None:
    cb = CallbackSet()
    await getattr(cb, fire_name)(*fire_args)


@pytest.mark.parametrize("on_name,fire_name,fire_args", EVENTS, ids=EVENT_IDS)
async def test_multiple_handlers_all_fire_in_order(on_name: str, fire_name: str, fire_args: tuple) -> None:
    cb = CallbackSet()
    order: list[int] = []

    async def first(*args: object) -> None:
        order.append(1)

    async def second(*args: object) -> None:
        order.append(2)

    getattr(cb, on_name)(first)
    getattr(cb, on_name)(second)
    await getattr(cb, fire_name)(*fire_args)

    assert order == [1, 2]


@pytest.mark.parametrize("on_name,fire_name,fire_args", EVENTS, ids=EVENT_IDS)
async def test_exception_swallowed_and_next_handler_fires(on_name: str, fire_name: str, fire_args: tuple) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    async def bad(*args: object) -> None:
        raise RuntimeError("handler failure")

    async def good(*args: object) -> None:
        fired.append(True)

    getattr(cb, on_name)(bad)
    getattr(cb, on_name)(good)
    await getattr(cb, fire_name)(*fire_args)

    assert fired == [True]


async def test_handler_registered_on_one_event_not_fired_by_another() -> None:
    cb = CallbackSet()
    invoked: list[bool] = []

    @cb.on_agent_response
    async def handler(response: object, iteration: int) -> None:
        invoked.append(True)

    await cb.fire_phase_start("p1")

    assert invoked == []


# ===========================================================================
# Callbacks container tests
# ===========================================================================


async def test_empty_callbacks_fire_is_noop() -> None:
    cb = Callbacks()
    await cb.fire_agent_response(_RESPONSE, 1)
    await cb.fire_tool_call(_TOOL_CALL, _TOOL_RESULT, 1)
    await cb.fire_complete(_REACT_RESULT)
    await cb.fire_error(_ERROR)
    await cb.fire_before_compact()
    await cb.fire_after_compact()
    await cb.fire_before_agent_send(1)
    await cb.fire_phase_start("p1")
    await cb.fire_phase_finish("p1")


async def test_single_set_receives_events() -> None:
    fired: list[str] = []
    cb = CallbackSet()

    @cb.on_phase_start
    async def record_start(phase_id: str) -> None:
        fired.append(f"start:{phase_id}")

    @cb.on_phase_finish
    async def record_finish(phase_id: str) -> None:
        fired.append(f"finish:{phase_id}")

    callbacks = Callbacks([cb])
    await callbacks.fire_phase_start("p1")
    await callbacks.fire_phase_finish("p1")

    assert fired == ["start:p1", "finish:p1"]


async def test_two_sets_both_receive_events() -> None:
    received_a: list[str] = []
    received_b: list[str] = []

    cb_a = CallbackSet()
    cb_b = CallbackSet()

    @cb_a.on_complete
    async def record_a(result: ReActResult) -> None:
        received_a.append("complete")

    @cb_b.on_complete
    async def record_b(result: ReActResult) -> None:
        received_b.append("complete")

    callbacks = Callbacks([cb_a, cb_b])
    await callbacks.fire_complete(_REACT_RESULT)

    assert received_a == ["complete"]
    assert received_b == ["complete"]


async def test_exception_in_one_set_does_not_block_other() -> None:
    received: list[bool] = []

    cb_bad = CallbackSet()
    cb_good = CallbackSet()

    @cb_bad.on_complete
    async def raise_always(result: ReActResult) -> None:
        raise RuntimeError("bad set")

    @cb_good.on_complete
    async def record(result: ReActResult) -> None:
        received.append(True)

    callbacks = Callbacks([cb_bad, cb_good])
    await callbacks.fire_complete(_REACT_RESULT)

    assert received == [True]
