# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import pytest

from ddev.ai.run_events import Answered, NotAnswered, Notice, Question, RunEvents, Unanswered


@dataclass(frozen=True)
class Progress(Notice):
    completed: int


@dataclass(frozen=True)
class ProgressWithTotal(Progress):
    total: int


@dataclass(frozen=True)
class Confirm(Question[bool]):
    label: str


@dataclass(frozen=True)
class Choose(Question[int]):
    pass


async def test_inline_subscriber_failure_does_not_stop_delivery(caplog: pytest.LogCaptureFixture):
    logger = logging.getLogger(__name__)
    events = RunEvents(logger=logger)
    seen: list[int] = []

    async def fail(notice: Progress) -> None:
        raise ValueError("cannot record progress")

    async def record(notice: Progress) -> None:
        seen.append(notice.completed)

    events.subscribe(Progress, fail)
    events.subscribe(Progress, record)
    await events.notify(Progress(4))

    assert seen == [4]
    assert (logger.name, logging.ERROR, "Subscriber failed for Progress") in caplog.record_tuples
    assert "cannot record progress" in caplog.text


async def test_background_notice_returns_before_delivery_and_drains_at_run_exit():
    release = asyncio.Event()
    seen: list[int] = []

    async def record(notice: Progress) -> None:
        await release.wait()
        seen.append(notice.completed)

    async with asyncio.timeout(5), asyncio.TaskGroup() as tasks:
        events = RunEvents(notice_task_group=tasks)
        events.subscribe(Progress, record)
        await events.notify(Progress(4), block=False)
        assert seen == []
        release.set()

    assert seen == [4]


async def test_background_subscriber_failure_does_not_cancel_other_deliveries(caplog: pytest.LogCaptureFixture):
    logger = logging.getLogger(__name__)
    started = asyncio.Event()
    failed = asyncio.Event()
    seen: list[int] = []

    async def record(notice: Progress) -> None:
        started.set()
        await failed.wait()
        seen.append(notice.completed)

    async def fail(notice: Progress) -> None:
        await started.wait()
        failed.set()
        raise ValueError("cannot record progress")

    async with asyncio.timeout(5), asyncio.TaskGroup() as tasks:
        events = RunEvents(logger=logger, notice_task_group=tasks)
        events.subscribe(Progress, record)
        events.subscribe(Progress, fail)
        await events.notify(Progress(4), block=False)

    assert seen == [4]
    assert (logger.name, logging.ERROR, "Subscriber failed for Progress") in caplog.record_tuples
    assert "cannot record progress" in caplog.text


async def test_background_delivery_is_cancelled_when_run_fails():
    started = asyncio.Event()
    waiting = asyncio.Event()
    cancelled = asyncio.Event()

    async def record(notice: Progress) -> None:
        started.set()
        try:
            await waiting.wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    with pytest.RaisesGroup(pytest.RaisesExc(RuntimeError, match="run failed")):
        async with asyncio.timeout(5), asyncio.TaskGroup() as tasks:
            events = RunEvents(notice_task_group=tasks)
            events.subscribe(Progress, record)
            await events.notify(Progress(4), block=False)
            await started.wait()
            raise RuntimeError("run failed")

    assert cancelled.is_set()


async def test_background_notice_requires_run_task_group():
    with pytest.raises(RuntimeError, match="Background notices require a run-owned task group"):
        await RunEvents().notify(Progress(4), block=False)


async def test_inline_subscribers_receive_notices_in_send_order():
    events = RunEvents()
    exact_progress: list[Progress] = []
    all_progress: list[Progress] = []

    async def record_exact_progress(notice: Progress) -> None:
        exact_progress.append(notice)

    async def record_all_progress(notice: Progress) -> None:
        all_progress.append(notice)

    events.subscribe(Progress, record_exact_progress)
    events.subscribe(Progress, record_all_progress, exact=False)
    first, detailed, last = Progress(1), ProgressWithTotal(2, total=5), Progress(3)
    await events.notify(first)
    await events.notify(detailed)
    await events.notify(last)

    assert exact_progress == [first, last]
    assert all_progress == [first, detailed, last]


async def test_question_subscriber_can_observe_all_question_types():
    events = RunEvents()
    seen: list[Question[Any]] = []

    async def observe(question: Question[Any]) -> None:
        seen.append(question)

    events.subscribe(Question, observe, exact=False)
    confirm, choose = Confirm("retry"), Choose()
    await events.ask(confirm, timeout=0)
    await events.notify(Progress(1))
    await events.ask(choose, timeout=0)

    assert seen == [confirm, choose]


@pytest.mark.parametrize("has_responder", [False, True])
async def test_observers_see_the_question_before_answering(has_responder: bool):
    events = RunEvents()
    seen: list[str] = []

    async def observe(question: Confirm) -> None:
        seen.append(question.label)

    async def decline(question: Confirm) -> bool:
        assert seen == [question.label]
        return False

    events.subscribe(Confirm, observe)
    if has_responder:
        events.respond(Confirm.answered_by(decline))

    result = await events.ask(Confirm("retry"), timeout=0)
    assert result == (Answered(False) if has_responder else NotAnswered(Unanswered.NO_RESPONDER))
    assert seen == ["retry"]


@pytest.mark.parametrize("failure", [ValueError("closed"), TimeoutError("responder's own timeout")])
async def test_responder_exception_is_not_an_answer(failure: Exception, caplog: pytest.LogCaptureFixture):
    events = RunEvents()

    async def fail(question: Confirm) -> bool:
        raise failure

    events.respond(Confirm.answered_by(fail))
    assert await events.ask(Confirm("retry"), timeout=10) == NotAnswered(Unanswered.RESPONDER_FAILED)
    assert str(failure) in caplog.text


async def test_expired_response_deadline_cancels_responder():
    events = RunEvents()
    waiting = asyncio.Event()
    cleaned_up = asyncio.Event()

    async def wait(question: Confirm) -> bool:
        try:
            await waiting.wait()
            return True
        finally:
            cleaned_up.set()

    events.respond(Confirm.answered_by(wait))
    assert await events.ask(Confirm("retry"), timeout=0) == NotAnswered(Unanswered.TIMED_OUT)
    assert cleaned_up.is_set()


def test_second_responder_for_same_question_is_rejected():
    events = RunEvents()

    async def confirm(question: Confirm) -> bool:
        return True

    events.respond(Confirm.answered_by(confirm))
    with pytest.raises(ValueError, match="already registered for Confirm"):
        events.respond(Confirm.answered_by(confirm))


async def test_questions_serialize_and_cancelling_one_releases_the_next():
    events = RunEvents()
    first_started = asyncio.Event()
    first_left = asyncio.Event()
    second_seen = asyncio.Event()
    waiting = asyncio.Event()

    async def confirm(question: Confirm) -> bool:
        first_started.set()
        try:
            await waiting.wait()
            return True
        finally:
            first_left.set()

    async def observe(question: Choose) -> None:
        second_seen.set()

    async def choose(question: Choose) -> int:
        assert first_left.is_set()
        return 2

    events.respond(Confirm.answered_by(confirm))
    events.subscribe(Choose, observe)
    events.respond(Choose.answered_by(choose))
    async with asyncio.timeout(5), asyncio.TaskGroup() as group:
        first = group.create_task(events.ask(Confirm("retry"), timeout=10))
        await first_started.wait()
        second = group.create_task(events.ask(Choose(), timeout=0))
        await second_seen.wait()
        assert not second.done()

        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert await second == Answered(2)


async def test_responder_cannot_ask_again_on_the_same_pipe():
    events = RunEvents()

    async def confirm(question: Confirm) -> bool:
        with pytest.raises(RuntimeError, match="cannot ask another question"):
            await events.ask(Choose(), timeout=0)
        return True

    events.respond(Confirm.answered_by(confirm))
    assert await events.ask(Confirm("retry"), timeout=1) == Answered(True)
