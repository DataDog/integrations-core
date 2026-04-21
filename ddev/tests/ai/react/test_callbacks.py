# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.react.callbacks import CallbackSet
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Minimal fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def response() -> AgentResponse:
    return AgentResponse(
        stop_reason=StopReason.END_TURN,
        text="",
        tool_calls=[],
        usage=TokenUsage(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


@pytest.fixture
def tool_call() -> ToolCall:
    return ToolCall(id="tc_01", name="read_file", input={})


@pytest.fixture
def react_result(response: AgentResponse) -> ReActResult:
    return ReActResult(
        final_response=response,
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


async def test_empty_callback_set_is_noop(
    response: AgentResponse, tool_call: ToolCall, react_result: ReActResult
) -> None:
    cb = CallbackSet()
    await cb.fire_agent_response(response, 1, "agent")
    await cb.fire_tool_call(tool_call, ToolResult(success=True, data="ok"), "demo", 1, "agent")
    await cb.fire_complete(react_result)
    await cb.fire_error(RuntimeError("boom"))


async def test_multiple_handlers_same_event_all_fire(response: AgentResponse) -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_agent_response
    async def first(response: AgentResponse, iteration: int, name: str) -> None:
        fired.append(1)

    @cb.on_agent_response
    async def second(response: AgentResponse, iteration: int, name: str) -> None:
        fired.append(2)

    @cb.on_agent_response
    async def third(response: AgentResponse, iteration: int, name: str) -> None:
        fired.append(3)

    await cb.fire_agent_response(response, 5, "agent")

    assert fired == [1, 2, 3]


async def test_handlers_receive_correct_arguments(response: AgentResponse) -> None:
    cb = CallbackSet()
    received: list[tuple] = []

    @cb.on_agent_response
    async def h(response: AgentResponse, iteration: int, name: str) -> None:
        received.append((response, iteration, name))

    await cb.fire_agent_response(response, 7, "agent")

    assert received == [(response, 7, "agent")]


# ---------------------------------------------------------------------------
# Exception-swallowing guarantee
# ---------------------------------------------------------------------------


async def test_fire_swallows_handler_exception(response: AgentResponse) -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_agent_response
    async def bad(response: AgentResponse, iteration: int, name: str) -> None:
        raise RuntimeError("boom")

    @cb.on_agent_response
    async def good(response: AgentResponse, iteration: int, name: str) -> None:
        fired.append(iteration)

    await cb.fire_agent_response(response, 1, "agent")
    assert fired == [1]


async def test_fire_tool_call_swallows_handler_exception(tool_call: ToolCall) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_tool_call
    async def bad(tool_call: ToolCall, result: ToolResult, display: str, iteration: int, name: str) -> None:
        raise RuntimeError("boom")

    @cb.on_tool_call
    async def good(tool_call: ToolCall, result: ToolResult, display: str, iteration: int, name: str) -> None:
        fired.append(True)

    await cb.fire_tool_call(tool_call, ToolResult(success=True, data="ok"), "demo", 1, "agent")
    assert fired == [True]


async def test_fire_complete_swallows_handler_exception(react_result: ReActResult) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_complete
    async def bad(result: ReActResult) -> None:
        raise RuntimeError("boom")

    @cb.on_complete
    async def good(result: ReActResult) -> None:
        fired.append(True)

    await cb.fire_complete(react_result)
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


# ---------------------------------------------------------------------------
# before_compact and after_compact
# ---------------------------------------------------------------------------


async def test_before_compact_registered_and_fired() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_before_compact
    async def h() -> None:
        fired.append(True)

    await cb.fire_before_compact()
    assert fired == [True]


async def test_after_compact_registered_and_fired() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_after_compact
    async def h() -> None:
        fired.append(True)

    await cb.fire_after_compact()
    assert fired == [True]


async def test_compact_callback_exception_is_swallowed() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_before_compact
    async def bad() -> None:
        raise RuntimeError("boom")

    @cb.on_before_compact
    async def good() -> None:
        fired.append(True)

    await cb.fire_before_compact()
    assert fired == [True]


async def test_multiple_compact_handlers_all_fired() -> None:
    cb = CallbackSet()
    fired: list[str] = []

    @cb.on_before_compact
    async def b1() -> None:
        fired.append("before-1")

    @cb.on_before_compact
    async def b2() -> None:
        fired.append("before-2")

    @cb.on_after_compact
    async def a1() -> None:
        fired.append("after-1")

    @cb.on_after_compact
    async def a2() -> None:
        fired.append("after-2")

    await cb.fire_before_compact()
    await cb.fire_after_compact()
    assert fired == ["before-1", "before-2", "after-1", "after-2"]
