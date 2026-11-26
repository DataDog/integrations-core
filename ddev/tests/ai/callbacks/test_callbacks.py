# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet

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
