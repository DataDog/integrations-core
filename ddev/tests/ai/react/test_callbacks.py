# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.react.callbacks import CallbackSet
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Minimal fixtures
# ---------------------------------------------------------------------------


def make_response() -> AgentResponse:
    return AgentResponse(
        stop_reason=StopReason.END_TURN,
        text="",
        tool_calls=[],
        usage=TokenUsage(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


def make_tool_call() -> ToolCall:
    return ToolCall(id="tc_01", name="read_file", input={})


def make_result() -> ReActResult:
    return ReActResult(
        final_response=make_response(),
        iterations=1,
        total_input_tokens=10,
        total_output_tokens=5,
        context_usage=None,
    )


# ---------------------------------------------------------------------------
# Registration via decorators
# ---------------------------------------------------------------------------


async def test_decorator_returns_original_function() -> None:
    cb = CallbackSet()

    async def handler(response: AgentResponse, iteration: int) -> None:
        pass

    assert cb.on_agent_response(handler) is handler


async def test_decorator_registers_handler_in_internal_list() -> None:
    cb = CallbackSet()

    @cb.on_agent_response
    async def h1(response: AgentResponse, iteration: int) -> None: ...

    @cb.on_agent_response
    async def h2(response: AgentResponse, iteration: int) -> None: ...

    assert cb._on_agent_response == [h1, h2]


# ---------------------------------------------------------------------------
# Dispatch ordering and isolation
# ---------------------------------------------------------------------------


async def test_empty_callback_set_is_noop() -> None:
    cb = CallbackSet()
    await cb.fire_agent_response(make_response(), 1)
    await cb.fire_tool_call(make_tool_call(), ToolResult(success=True, data="ok"), 1)
    await cb.fire_complete(make_result())
    await cb.fire_error(RuntimeError("boom"))


async def test_multiple_handlers_same_event_all_fire() -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_agent_response
    async def first(response: AgentResponse, iteration: int) -> None:
        fired.append(1)

    @cb.on_agent_response
    async def second(response: AgentResponse, iteration: int) -> None:
        fired.append(2)

    @cb.on_agent_response
    async def third(response: AgentResponse, iteration: int) -> None:
        fired.append(3)

    await cb.fire_agent_response(make_response(), 5)

    assert fired == [1, 2, 3]


async def test_handlers_receive_correct_arguments() -> None:
    cb = CallbackSet()
    received: list[tuple] = []

    @cb.on_agent_response
    async def h(response: AgentResponse, iteration: int) -> None:
        received.append((response, iteration))

    response = make_response()
    await cb.fire_agent_response(response, 7)

    assert received == [(response, 7)]


# ---------------------------------------------------------------------------
# Exception-swallowing guarantee
# ---------------------------------------------------------------------------


async def test_fire_swallows_handler_exception() -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_agent_response
    async def bad(response: AgentResponse, iteration: int) -> None:
        raise RuntimeError("boom")

    @cb.on_agent_response
    async def good(response: AgentResponse, iteration: int) -> None:
        fired.append(iteration)

    await cb.fire_agent_response(make_response(), 1)
    assert fired == [1]


async def test_fire_tool_call_swallows_handler_exception() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_tool_call
    async def bad(tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        raise RuntimeError("boom")

    @cb.on_tool_call
    async def good(tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        fired.append(True)

    await cb.fire_tool_call(make_tool_call(), ToolResult(success=True, data="ok"), 1)
    assert fired == [True]


async def test_fire_complete_swallows_handler_exception() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_complete
    async def bad(result: ReActResult) -> None:
        raise RuntimeError("boom")

    @cb.on_complete
    async def good(result: ReActResult) -> None:
        fired.append(True)

    await cb.fire_complete(make_result())
    assert fired == [True]


async def test_fire_error_swallows_handler_exception() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_error
    async def bad(error: BaseException) -> None:
        raise RuntimeError("boom")

    @cb.on_error
    async def good(error: BaseException) -> None:
        fired.append(True)

    await cb.fire_error(ValueError("original error"))
    assert fired == [True]
