# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Minimal fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scope() -> AgentScope:
    return AgentScope(owner_id="p1", role=AgentRole.PHASE, phase_id="p1")


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

    async def handler(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        pass

    assert cb.on_agent_response(handler) is handler


async def test_decorator_registers_handler_in_internal_list() -> None:
    cb = CallbackSet()

    @cb.on_agent_response
    async def h1(scope: AgentScope, response: AgentResponse, iteration: int) -> None: ...

    @cb.on_agent_response
    async def h2(scope: AgentScope, response: AgentResponse, iteration: int) -> None: ...

    assert cb._on_agent_response == [h1, h2]


# ---------------------------------------------------------------------------
# Dispatch ordering and isolation
# ---------------------------------------------------------------------------


async def test_empty_callback_set_is_noop(
    scope: AgentScope, response: AgentResponse, tool_call: ToolCall, react_result: ReActResult
) -> None:
    cb = CallbackSet()
    await cb.fire_agent_start(scope, "sys", [])
    await cb.fire_agent_response(scope, response, 1)
    await cb.fire_tool_call(scope, tool_call, ToolResult(success=True, data="ok"), 1)
    await cb.fire_agent_finish(scope, react_result)
    await cb.fire_agent_error(scope, RuntimeError("boom"))


async def test_multiple_handlers_same_event_all_fire(scope: AgentScope, response: AgentResponse) -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_agent_response
    async def first(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        fired.append(1)

    @cb.on_agent_response
    async def second(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        fired.append(2)

    @cb.on_agent_response
    async def third(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        fired.append(3)

    await cb.fire_agent_response(scope, response, 5)

    assert fired == [1, 2, 3]


async def test_handlers_receive_correct_arguments(scope: AgentScope, response: AgentResponse) -> None:
    cb = CallbackSet()
    received: list[tuple] = []

    @cb.on_agent_response
    async def h(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        received.append((scope, response, iteration))

    await cb.fire_agent_response(scope, response, 7)

    assert received == [(scope, response, 7)]


# ---------------------------------------------------------------------------
# Exception-swallowing guarantee
# ---------------------------------------------------------------------------


async def test_fire_swallows_handler_exception(scope: AgentScope, response: AgentResponse) -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_agent_response
    async def bad(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        raise RuntimeError("boom")

    @cb.on_agent_response
    async def good(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        fired.append(iteration)

    await cb.fire_agent_response(scope, response, 1)
    assert fired == [1]


async def test_fire_tool_call_swallows_handler_exception(scope: AgentScope, tool_call: ToolCall) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_tool_call
    async def bad(scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        raise RuntimeError("boom")

    @cb.on_tool_call
    async def good(scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        fired.append(True)

    await cb.fire_tool_call(scope, tool_call, ToolResult(success=True, data="ok"), 1)
    assert fired == [True]


async def test_fire_agent_finish_swallows_handler_exception(scope: AgentScope, react_result: ReActResult) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_agent_finish
    async def bad(scope: AgentScope, result: ReActResult) -> None:
        raise RuntimeError("boom")

    @cb.on_agent_finish
    async def good(scope: AgentScope, result: ReActResult) -> None:
        fired.append(True)

    await cb.fire_agent_finish(scope, react_result)
    assert fired == [True]


async def test_fire_agent_error_swallows_handler_exception(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_agent_error
    async def bad(scope: AgentScope, error: BaseException) -> None:
        raise RuntimeError("boom")

    @cb.on_agent_error
    async def good(scope: AgentScope, error: BaseException) -> None:
        fired.append(True)

    await cb.fire_agent_error(scope, ValueError("original error"))
    assert fired == [True]


# ---------------------------------------------------------------------------
# on_agent_start
# ---------------------------------------------------------------------------


async def test_agent_start_registered_and_fired(scope: AgentScope) -> None:
    cb = CallbackSet()
    received: list[tuple] = []

    @cb.on_agent_start
    async def h(scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
        received.append((scope, system_prompt, tools))

    await cb.fire_agent_start(scope, "sys", ["read_file"])
    assert received == [(scope, "sys", ["read_file"])]


# ---------------------------------------------------------------------------
# before_compact and after_compact
# ---------------------------------------------------------------------------


async def test_before_compact_registered_and_fired(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[AgentScope] = []

    @cb.on_before_compact
    async def h(scope: AgentScope) -> None:
        fired.append(scope)

    await cb.fire_before_compact(scope)
    assert fired == [scope]


async def test_after_compact_registered_and_fired(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[AgentScope] = []

    @cb.on_after_compact
    async def h(scope: AgentScope) -> None:
        fired.append(scope)

    await cb.fire_after_compact(scope)
    assert fired == [scope]


async def test_context_cleared_registered_and_fired(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[AgentScope] = []

    @cb.on_context_cleared
    async def h(scope: AgentScope) -> None:
        fired.append(scope)

    await cb.fire_context_cleared(scope)
    assert fired == [scope]


async def test_context_cleared_callback_exception_is_swallowed(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_context_cleared
    async def bad(scope: AgentScope) -> None:
        raise RuntimeError("boom")

    @cb.on_context_cleared
    async def good(scope: AgentScope) -> None:
        fired.append(True)

    await cb.fire_context_cleared(scope)
    assert fired == [True]


async def test_compact_callback_exception_is_swallowed(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_before_compact
    async def bad(scope: AgentScope) -> None:
        raise RuntimeError("boom")

    @cb.on_before_compact
    async def good(scope: AgentScope) -> None:
        fired.append(True)

    await cb.fire_before_compact(scope)
    assert fired == [True]


async def test_multiple_compact_handlers_all_fired(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[str] = []

    @cb.on_before_compact
    async def b1(scope: AgentScope) -> None:
        fired.append("before-1")

    @cb.on_before_compact
    async def b2(scope: AgentScope) -> None:
        fired.append("before-2")

    @cb.on_after_compact
    async def a1(scope: AgentScope) -> None:
        fired.append("after-1")

    @cb.on_after_compact
    async def a2(scope: AgentScope) -> None:
        fired.append("after-2")

    await cb.fire_before_compact(scope)
    await cb.fire_after_compact(scope)
    assert fired == ["before-1", "before-2", "after-1", "after-2"]


# ---------------------------------------------------------------------------
# on_phase_start
# ---------------------------------------------------------------------------


async def test_phase_start_registered_and_fired() -> None:
    cb = CallbackSet()
    fired: list[str] = []

    @cb.on_phase_start
    async def h(phase_id: str) -> None:
        fired.append(phase_id)

    await cb.fire_phase_start("my-phase")
    assert fired == ["my-phase"]


async def test_phase_start_receives_correct_phase_id() -> None:
    cb = CallbackSet()
    received: list[str] = []

    @cb.on_phase_start
    async def h(phase_id: str) -> None:
        received.append(phase_id)

    await cb.fire_phase_start("draft")
    assert received == ["draft"]


async def test_phase_start_multiple_handlers_all_fire_in_order() -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_phase_start
    async def first(phase_id: str) -> None:
        fired.append(1)

    @cb.on_phase_start
    async def second(phase_id: str) -> None:
        fired.append(2)

    @cb.on_phase_start
    async def third(phase_id: str) -> None:
        fired.append(3)

    await cb.fire_phase_start("p")
    assert fired == [1, 2, 3]


async def test_phase_start_exception_is_swallowed() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_phase_start
    async def bad(phase_id: str) -> None:
        raise RuntimeError("boom")

    @cb.on_phase_start
    async def good(phase_id: str) -> None:
        fired.append(True)

    await cb.fire_phase_start("p")
    assert fired == [True]


# ---------------------------------------------------------------------------
# on_phase_finish
# ---------------------------------------------------------------------------


async def test_phase_finish_registered_and_fired() -> None:
    cb = CallbackSet()
    fired: list[str] = []

    @cb.on_phase_finish
    async def h(phase_id: str) -> None:
        fired.append(phase_id)

    await cb.fire_phase_finish("my-phase")
    assert fired == ["my-phase"]


async def test_phase_finish_receives_correct_phase_id() -> None:
    cb = CallbackSet()
    received: list[str] = []

    @cb.on_phase_finish
    async def h(phase_id: str) -> None:
        received.append(phase_id)

    await cb.fire_phase_finish("write-code")
    assert received == ["write-code"]


async def test_phase_finish_multiple_handlers_all_fire_in_order() -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_phase_finish
    async def first(phase_id: str) -> None:
        fired.append(1)

    @cb.on_phase_finish
    async def second(phase_id: str) -> None:
        fired.append(2)

    @cb.on_phase_finish
    async def third(phase_id: str) -> None:
        fired.append(3)

    await cb.fire_phase_finish("p")
    assert fired == [1, 2, 3]


async def test_phase_finish_exception_is_swallowed() -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_phase_finish
    async def bad(phase_id: str) -> None:
        raise RuntimeError("boom")

    @cb.on_phase_finish
    async def good(phase_id: str) -> None:
        fired.append(True)

    await cb.fire_phase_finish("p")
    assert fired == [True]


# ---------------------------------------------------------------------------
# on_phase_error and on_run_error
# ---------------------------------------------------------------------------


async def test_phase_error_registered_and_fired() -> None:
    cb = CallbackSet()
    received: list[tuple[str, BaseException]] = []
    error = RuntimeError("boom")

    @cb.on_phase_error
    async def handler(phase_id: str, error: BaseException) -> None:
        received.append((phase_id, error))

    await cb.fire_phase_error("inspect", error)

    assert received == [("inspect", error)]


async def test_run_error_registered_and_fired() -> None:
    cb = CallbackSet()
    received: list[bool] = []

    @cb.on_run_error
    async def handler() -> None:
        received.append(True)

    await cb.fire_run_error()

    assert received == [True]


async def test_error_callback_exceptions_are_swallowed() -> None:
    cb = CallbackSet()
    fired: list[str] = []

    @cb.on_phase_error
    async def bad_phase(phase_id: str, error: BaseException) -> None:
        raise RuntimeError("callback failed")

    @cb.on_phase_error
    async def good_phase(phase_id: str, error: BaseException) -> None:
        fired.append(f"phase:{phase_id}")

    @cb.on_run_error
    async def bad_run() -> None:
        raise RuntimeError("callback failed")

    @cb.on_run_error
    async def good_run() -> None:
        fired.append("run")

    error = RuntimeError("boom")
    await cb.fire_phase_error("inspect", error)
    await cb.fire_run_error()

    assert fired == ["phase:inspect", "run"]


# ---------------------------------------------------------------------------
# on_before_agent_send
# ---------------------------------------------------------------------------


async def test_before_agent_send_registered_and_fired(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_before_agent_send
    async def h(scope: AgentScope, prompt: str, iteration: int) -> None:
        fired.append(iteration)

    await cb.fire_before_agent_send(scope, "do it", 3)
    assert fired == [3]


async def test_before_agent_send_receives_correct_prompt_and_iteration(scope: AgentScope) -> None:
    cb = CallbackSet()
    received: list[tuple[str, int]] = []

    @cb.on_before_agent_send
    async def h(scope: AgentScope, prompt: str, iteration: int) -> None:
        received.append((prompt, iteration))

    await cb.fire_before_agent_send(scope, "summarize", 7)
    assert received == [("summarize", 7)]


async def test_before_agent_send_multiple_handlers_all_fire_in_order(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[int] = []

    @cb.on_before_agent_send
    async def first(scope: AgentScope, prompt: str, iteration: int) -> None:
        fired.append(1)

    @cb.on_before_agent_send
    async def second(scope: AgentScope, prompt: str, iteration: int) -> None:
        fired.append(2)

    @cb.on_before_agent_send
    async def third(scope: AgentScope, prompt: str, iteration: int) -> None:
        fired.append(3)

    await cb.fire_before_agent_send(scope, "p", 1)
    assert fired == [1, 2, 3]


async def test_before_agent_send_exception_is_swallowed(scope: AgentScope) -> None:
    cb = CallbackSet()
    fired: list[bool] = []

    @cb.on_before_agent_send
    async def bad(scope: AgentScope, prompt: str, iteration: int) -> None:
        raise RuntimeError("boom")

    @cb.on_before_agent_send
    async def good(scope: AgentScope, prompt: str, iteration: int) -> None:
        fired.append(True)

    await cb.fire_before_agent_send(scope, "p", 1)
    assert fired == [True]


# ---------------------------------------------------------------------------
# on_before_goal_check and on_after_goal_check
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event", ["before", "after"], ids=["before", "after"])
async def test_goal_check_callbacks_register_fire_and_swallow_exceptions(event):
    cb = CallbackSet()
    fired: list = []

    decorator = cb.on_before_goal_check if event == "before" else cb.on_after_goal_check

    @decorator
    async def bad(*args):
        raise RuntimeError("boom")

    @decorator
    async def good(*args):
        fired.append(args)

    if event == "before":
        await cb.fire_before_goal_check("phase-a", "task-x", 3)
        assert fired == [("phase-a", "task-x", 3)]
    else:
        await cb.fire_after_goal_check("phase-a", "task-x", 3, False, "missing y")
        assert fired == [("phase-a", "task-x", 3, False, "missing y")]


async def test_callbacks_dispatches_goal_check_to_all_sets():
    s1, s2 = CallbackSet(), CallbackSet()
    fired: list = []

    @s1.on_before_goal_check
    async def h1(phase_id, name, attempt):
        fired.append(("s1", phase_id, name, attempt))

    @s2.on_after_goal_check
    async def h2(phase_id, name, attempt, valid, reason):
        fired.append(("s2", phase_id, name, attempt, valid, reason))

    cb = Callbacks([s1, s2])
    await cb.fire_before_goal_check("phase-a", "t", 1)
    await cb.fire_after_goal_check("phase-a", "t", 1, True, "")
    assert fired == [
        ("s1", "phase-a", "t", 1),
        ("s2", "phase-a", "t", 1, True, ""),
    ]


async def test_goal_callbacks_distinguish_duplicate_task_names_across_phases():
    callback_set = CallbackSet()
    fired: list[tuple[str, str]] = []

    @callback_set.on_before_goal_check
    async def record(phase_id: str, task_name: str, attempt: int) -> None:
        fired.append((phase_id, task_name))

    callbacks = Callbacks([callback_set])
    await callbacks.fire_before_goal_check("phase-a", "review", 1)
    await callbacks.fire_before_goal_check("phase-b", "review", 1)

    assert fired == [("phase-a", "review"), ("phase-b", "review")]


# ---------------------------------------------------------------------------
# Callbacks container
# ---------------------------------------------------------------------------


async def test_callbacks_empty_is_noop(
    scope: AgentScope, response: AgentResponse, tool_call: ToolCall, react_result: ReActResult
) -> None:
    callbacks = Callbacks()
    await callbacks.fire_agent_start(scope, "sys", [])
    await callbacks.fire_agent_response(scope, response, 1)
    await callbacks.fire_tool_call(scope, tool_call, ToolResult(success=True, data="ok"), 1)
    await callbacks.fire_agent_finish(scope, react_result)
    await callbacks.fire_agent_error(scope, RuntimeError("boom"))
    await callbacks.fire_before_compact(scope)
    await callbacks.fire_after_compact(scope)
    await callbacks.fire_context_cleared(scope)
    await callbacks.fire_before_agent_send(scope, "p", 1)
    await callbacks.fire_phase_start("p")
    await callbacks.fire_phase_finish("p")
    await callbacks.fire_phase_error("p", RuntimeError("boom"))
    await callbacks.fire_run_error()
    await callbacks.fire_before_goal_check("p", "t", 1)
    await callbacks.fire_after_goal_check("p", "t", 1, True, "")


async def test_callbacks_dispatches_to_all_sets(scope: AgentScope, response: AgentResponse) -> None:
    fired_a: list[int] = []
    fired_b: list[int] = []

    set_a = CallbackSet()
    set_b = CallbackSet()

    @set_a.on_agent_response
    async def a(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        fired_a.append(iteration)

    @set_b.on_agent_response
    async def b(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        fired_b.append(iteration)

    callbacks = Callbacks([set_a, set_b])
    await callbacks.fire_agent_response(scope, response, 3)

    assert fired_a == [3]
    assert fired_b == [3]


async def test_callbacks_set_with_no_registered_handlers_is_noop(scope: AgentScope, response: AgentResponse) -> None:
    callbacks = Callbacks([CallbackSet()])
    await callbacks.fire_agent_response(scope, response, 1)


async def test_with_set_appends_without_mutating_original(scope: AgentScope, response: AgentResponse) -> None:
    fired: list[int] = []
    extra = CallbackSet()

    @extra.on_agent_response
    async def h(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        fired.append(iteration)

    base = Callbacks()
    combined = base.with_set(extra)

    # Original is untouched (no handlers), combined dispatches to the new set.
    await base.fire_agent_response(scope, response, 1)
    assert fired == []
    await combined.fire_agent_response(scope, response, 2)
    assert fired == [2]
    assert base._sets == []
