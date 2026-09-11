# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging
import math
import os
import signal
import sys
import threading
import time
from collections.abc import Callable, Generator
from concurrent.futures import Executor, ThreadPoolExecutor
from contextlib import AbstractContextManager, contextmanager, suppress
from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from types import FrameType

import pytest
from pytest_mock import MockerFixture

from ddev.event_bus.exceptions import (
    FatalProcessingError,
    HookExecutionError,
    HookName,
    MessageProcessingError,
    OrchestratorHookError,
    ProcessorHookError,
    ProcessorQueueError,
    SkipMessageError,
)
from ddev.event_bus.orchestrator import (
    DEFAULT_ORCHESTRATOR_MAX_TIMEOUT,
    AsyncProcessor,
    BaseMessage,
    EventBusOrchestrator,
    MessageScope,
    SyncProcessor,
)
from ddev.event_bus.shutdown import ShutdownKind, ShutdownRequest
from ddev.monitoring import ComponentMonitor, MonitoringRuntime
from tests.helpers.monitoring import RecordingSink

# Test Structure Documentation
# --------------------------
#
# This test module uses a semantic structure to simulate a realistic event bus scenario
# modeled after an office/company communication system.
#
# Messages:
# - Memo: An internal memo with a 'subject' and 'content'.
# - TaskAssignment: A task assigned to someone. Contains a 'task_type' and 'priority'.
# - Announcement: A company-wide announcement. Contains an 'announcement_type' and 'urgent' flag.
#
# Processors:
# - Secretary:
#   - Subscribes to: Memo
#   - Action: Distributes memos. Tracks delivered memos, confirmations, and failures.
#   - Hooks: Implements custom on_success and on_error hooks for testing hook failures.
#
# - Analyst:
#   - Subscribes to: TaskAssignment, Announcement
#   - Action: Handles task assignments and announcements. Tracks completed tasks.
#   - Error Handling: Uses default on_success and on_error hooks (unless overridden in specific tests).
#
# - Manager:
#   - Subscribes to: Memo (in specific test cases)
#   - Action: Demonstrates message chaining. When a Manager receives a specific Memo, they delegate
#             by submitting new TaskAssignment and Announcement messages.
#
# Diagram:
#
# [Orchestrator]
#      |
#      +---(Memo)----> [Secretary]
#      |                   |
#      |                   +--> (Success/Error Hooks)
#      |
#      +---(TaskAssignment, Announcement)----> [Analyst]
#      |
#      +---(Memo)----> [Manager] --(TaskAssignment, Announcement)--> [Analyst]


@dataclass
class Memo(BaseMessage):
    subject: str = ""
    content: str = "default"


@dataclass
class TaskAssignment(BaseMessage):
    task_type: str = ""
    priority: int = 0


@dataclass
class Announcement(BaseMessage):
    announcement_type: str = ""
    urgent: bool = False


class Secretary(AsyncProcessor[Memo]):
    def __init__(self, name: str):
        super().__init__(name)
        self.delivered_memos: list[BaseMessage] = []
        self.confirmations: list[BaseMessage] = []
        self.failed_deliveries: list[tuple[BaseMessage, Exception]] = []
        self.hook_failures: list[ProcessorHookError] = []

    async def process_message(self, message: Memo):
        if message.content.startswith("fail_processing"):
            raise ValueError("Processing failed intentionally")
        self.delivered_memos.append(message)

    async def on_success(self, message: Memo):
        if message.content == "fail_success_hook":
            raise RuntimeError("Success hook failed intentionally")
        self.confirmations.append(message)

    async def on_error(self, error: MessageProcessingError | ProcessorHookError):
        if isinstance(error, MessageProcessingError):
            if error.message.content == "fail_processing_and_error":
                raise RuntimeError("Error hook failed intentionally")
            self.failed_deliveries.append((error.message, error.original_exception))
        else:
            self.hook_failures.append(error)


class Analyst(AsyncProcessor[TaskAssignment | Announcement]):
    def __init__(self, name: str):
        super().__init__(name)
        self.completed_tasks: list[BaseMessage] = []

    async def process_message(self, message: TaskAssignment | Announcement):
        if isinstance(message, TaskAssignment) and message.priority < 0:
            raise ValueError("Analyst failed intentionally")
        self.completed_tasks.append(message)


class Manager(AsyncProcessor[Memo]):
    def __init__(self, name: str):
        super().__init__(name)
        self.processed_memos: list[Memo] = []

    async def process_message(self, message: Memo):
        self.processed_memos.append(message)
        if message.subject == "new_hire":
            self.submit_message(Announcement(id="new_hire", urgent=False, announcement_type="NewHireAnnouncement"))
        else:
            self.submit_message(TaskAssignment(id="delegated_task", priority=100, task_type="DelegatedTask"))


class MockOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        logger: logging.Logger,
        max_timeout: float | None = DEFAULT_ORCHESTRATOR_MAX_TIMEOUT,
        grace_period: float = 10,
        fail_fast: bool = False,
        executor: Executor | None = None,
        message_scope: MessageScope | None = None,
    ):
        super().__init__(
            logger=logger,
            max_timeout=max_timeout,
            grace_period=grace_period,
            fail_fast=fail_fast,
            executor=executor,
            message_scope=message_scope,
        )
        self.events: list[str] = []
        self.received_messages: list[BaseMessage] = []
        self.finalized_exception: Exception | None = None

    async def on_initialize(self):
        self.events.append("initialize")

    async def on_finalize(self, exception: Exception | None):
        self.events.append("finalize")
        self.finalized_exception = exception

    async def on_message_received(self, message: BaseMessage):
        self.events.append(f"received_{message.id}")
        self.received_messages.append(message)


@pytest.fixture
def secretary() -> Secretary:
    return Secretary("secretary")


@pytest.fixture
def analyst() -> Analyst:
    return Analyst("analyst")


@pytest.fixture
def manager() -> Manager:
    return Manager("manager")


@pytest.fixture
def bare_orchestrator() -> MockOrchestrator:
    logger = logging.getLogger("test")
    return MockOrchestrator(logger, grace_period=0.1)


@pytest.fixture
def orchestrator(secretary: Secretary, analyst: Analyst, manager: Manager) -> MockOrchestrator:
    logger = logging.getLogger("test_orchestrator")
    # Use a short grace_period for tests to speed them up (0.1s instead of default 10s)
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    orchestrator.register_processor(secretary, [Memo])
    orchestrator.register_processor(analyst, [TaskAssignment, Announcement])
    orchestrator.register_processor(manager, [Memo])

    return orchestrator


@contextmanager
def assert_time(lower_limit: float, upper_limit: float) -> Generator[None]:
    start = time.perf_counter()
    yield
    end = time.perf_counter()

    elapsed = end - start
    assert elapsed >= lower_limit
    assert elapsed <= upper_limit


def test_workflow_success(
    orchestrator: MockOrchestrator,
    secretary: Secretary,
    analyst: Analyst,
    manager: Manager,
):
    new_hire_memo = Memo("new_hire_memo", subject="new_hire", content="Welcome John!")

    orchestrator.submit_message(new_hire_memo)
    orchestrator.run()

    # Check Orchestrator State
    assert "initialize" in orchestrator.events
    assert "finalize" in orchestrator.events

    # Check Secretary State
    assert len(secretary.delivered_memos) == 1
    assert new_hire_memo in secretary.delivered_memos
    assert len(secretary.confirmations) == 1
    assert len(secretary.failed_deliveries) == 0

    # Check Analyst State
    # Received one announcement about the new hire
    assert len(analyst.completed_tasks) == 1
    assert isinstance(analyst.completed_tasks[0], Announcement)
    assert analyst.completed_tasks[0].id == "new_hire"

    # Check Manager State
    assert len(manager.processed_memos) == 1

    assert orchestrator.shutdown_request is None


@pytest.mark.parametrize(
    "memo_content, expected_error_type",
    [
        ("fail_processing", ValueError),
    ],
)
def test_processor_processing_failure(
    orchestrator: MockOrchestrator,
    secretary: Secretary,
    memo_content: str,
    expected_error_type: type[Exception],
):
    """Secretary's on_error returns cleanly, so the failure is handled and the bus continues."""
    orchestrator.submit_message(Memo("failed_memo", content=memo_content))

    orchestrator.run()

    assert len(secretary.delivered_memos) == 0
    assert len(secretary.confirmations) == 0
    assert len(secretary.failed_deliveries) == 1
    assert orchestrator.finalized_exception is None

    failed_msg, error = secretary.failed_deliveries[0]
    assert failed_msg.id == "failed_memo"
    assert isinstance(error, expected_error_type)


def test_processor_success_hook_failure_routed_to_on_error(orchestrator: MockOrchestrator, secretary: Secretary):
    """on_success failure is wrapped and routed to the processor's on_error."""
    orchestrator.submit_message(Memo("hook_fail_memo", content="fail_success_hook"))

    orchestrator.run()

    # process_message succeeded but on_success failed
    assert len(secretary.delivered_memos) == 1
    assert len(secretary.confirmations) == 0
    # Routed as a ProcessorHookError, not a MessageProcessingError
    assert len(secretary.failed_deliveries) == 0
    assert len(secretary.hook_failures) == 1

    hook_err = secretary.hook_failures[0]
    assert hook_err.hook_name is HookName.ON_SUCCESS
    assert isinstance(hook_err.original_exception, RuntimeError)
    assert isinstance(hook_err, ProcessorHookError)
    assert isinstance(hook_err, HookExecutionError)
    # Bus continues — Secretary handled the failure
    assert orchestrator.finalized_exception is None


def test_mixed_messages(orchestrator: MockOrchestrator, secretary: Secretary, analyst: Analyst):
    orchestrator.submit_message(Memo("memo1"))
    orchestrator.submit_message(TaskAssignment("task1"))
    orchestrator.submit_message(Announcement("announcement1"))
    orchestrator.submit_message(Memo("memo2"))

    orchestrator.run()

    assert len(secretary.delivered_memos) == 2
    # 2 explicit tasks + 2 delegated tasks from Manager (triggered by the 2 memos)
    assert len(analyst.completed_tasks) == 4


@pytest.mark.parametrize(
    "max_timeout, grace_period, upper_limit",
    [(10, 1, 5.5), (6, 5, 6.5)],
    ids=["waits_grace_period", "max_timeout_reached"],
)
def test_orchestrator_timing(
    orchestrator: MockOrchestrator,
    max_timeout: int,
    grace_period: int,
    upper_limit: int,
):
    orchestrator._max_timeout = max_timeout
    orchestrator._grace_period = grace_period

    time_start = time.perf_counter()
    orchestrator.run()
    time_end = time.perf_counter()
    assert time_end - time_start <= upper_limit


@pytest.mark.parametrize(
    "max_timeout, grace_period, expectation",
    [
        (10, 5, does_not_raise()),
        (10, 0, does_not_raise()),
        (0, 5, pytest.raises(ValueError)),
        (-1, 5, pytest.raises(ValueError)),
        (10, -1, pytest.raises(ValueError)),
        (5, 10, pytest.raises(ValueError)),
        (5, 5, pytest.raises(ValueError)),
    ],
    ids=[
        "valid_parameters",
        "grace_period_zero",
        "max_timeout_zero",
        "max_timeout_negative",
        "grace_period_negative",
        "max_timeout_less_than_grace_period",
        "max_timeout_equal_to_grace_period",
    ],
)
def test_validate_parameters(max_timeout: float, grace_period: float, expectation: AbstractContextManager):
    logger = logging.getLogger("test")
    with expectation:
        MockOrchestrator(logger, max_timeout=max_timeout, grace_period=grace_period)


def test_none_max_timeout_runs_unbounded():
    """max_timeout=None runs with no overall time limit."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, max_timeout=None, grace_period=0.1)

    assert orchestrator._max_timeout == math.inf


def test_unbounded_still_stops_via_grace_period():
    """Unbounded mode still exits when the queue is empty and the grace period elapses."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, max_timeout=None, grace_period=0.1)

    with assert_time(0.0, 1.0):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None


def test_default_on_error_with_default_policy_logs_and_continues(
    orchestrator: MockOrchestrator, analyst: Analyst, caplog: pytest.LogCaptureFixture
):
    """Analyst uses the default re-raising on_error; under fail_fast=False the bus logs and continues."""
    orchestrator.submit_message(TaskAssignment("bad_task", priority=-1))
    orchestrator.run()

    assert len(analyst.completed_tasks) == 0
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None
    assert "Analyst failed intentionally" in caplog.text


def test_default_on_error_with_fail_fast_stops_bus(secretary: Secretary, analyst: Analyst, manager: Manager):
    """Default on_error re-raises; under fail_fast=True the bus stops."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)
    orchestrator.register_processor(analyst, [TaskAssignment, Announcement])

    orchestrator.submit_message(TaskAssignment("bad_task", priority=-1))

    with pytest.raises(MessageProcessingError) as exc_info:
        orchestrator.run()

    assert isinstance(exc_info.value.original_exception, ValueError)
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is exc_info.value


def test_processor_on_error_failure_logs_under_default_policy(
    orchestrator: MockOrchestrator, secretary: Secretary, caplog: pytest.LogCaptureFixture
):
    """on_error itself raising a non-Fatal error is logged under fail_fast=False; bus continues."""
    orchestrator.submit_message(Memo("double_fail_memo", content="fail_processing_and_error"))

    orchestrator.run()

    assert len(secretary.delivered_memos) == 0
    assert len(secretary.failed_deliveries) == 0
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None
    assert "Error hook failed intentionally" in caplog.text


def test_processor_on_error_failure_stops_bus_under_fail_fast(secretary: Secretary):
    """on_error itself raising a non-Fatal error stops the bus when fail_fast=True."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)
    orchestrator.register_processor(secretary, [Memo])

    orchestrator.submit_message(Memo("double_fail_memo", content="fail_processing_and_error"))

    with pytest.raises(RuntimeError, match="Error hook failed intentionally"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert isinstance(orchestrator.finalized_exception, RuntimeError)


def test_on_error_returning_cleanly_continues_under_fail_fast(secretary: Secretary):
    """A processor whose on_error returns cleanly keeps the bus running even with fail_fast=True."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)
    orchestrator.register_processor(secretary, [Memo])

    orchestrator.submit_message(Memo("recoverable_memo", content="fail_processing"))
    orchestrator.submit_message(Memo("ok_memo", content="ok"))

    orchestrator.run()

    assert orchestrator.finalized_exception is None
    assert len(secretary.delivered_memos) == 1
    assert secretary.delivered_memos[0].id == "ok_memo"
    assert len(secretary.failed_deliveries) == 1


def test_processor_on_error_recovers_processing_failure(orchestrator: MockOrchestrator, secretary: Secretary):
    """process_message() failures handled by on_error keep the bus running normally."""
    orchestrator.submit_message(Memo("recoverable_memo", content="fail_processing"))
    orchestrator.submit_message(Memo("ok_memo", content="ok"))

    orchestrator.run()

    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None
    assert len(secretary.delivered_memos) == 1
    assert secretary.delivered_memos[0].id == "ok_memo"
    assert len(secretary.failed_deliveries) == 1


def test_no_subscribers():
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    # Should exit immediately
    with assert_time(0.0, 0.5):
        orchestrator.run()

    assert "initialize" in orchestrator.events
    assert "finalize" in orchestrator.events
    assert len(orchestrator.received_messages) == 0


@pytest.mark.parametrize(
    "hook_name, hook_attr",
    [
        (HookName.ON_INITIALIZE, "on_initialize"),
        (HookName.ON_MESSAGE_RECEIVED, "on_message_received"),
        (HookName.ON_FINALIZE, "on_finalize"),
    ],
    ids=["on_initialize", "on_message_received", "on_finalize"],
)
def test_orchestrator_hook_failure_surfaces_under_fail_fast(
    hook_name: HookName,
    hook_attr: str,
):
    """Each orchestrator-level hook surfaces its failure through run() when fail_fast=True."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)

    async def hook_boom(*_args, **_kwargs):
        raise RuntimeError(f"{hook_attr} boom")

    setattr(orchestrator, hook_attr, hook_boom)

    if hook_name is HookName.ON_MESSAGE_RECEIVED:
        secretary = Secretary("secretary")
        orchestrator.register_processor(secretary, [Memo])
        orchestrator.submit_message(Memo("trigger"))
    else:
        secretary = None

    with pytest.raises(OrchestratorHookError) as exc_info:
        orchestrator.run()

    assert exc_info.value.hook_name is hook_name
    assert isinstance(exc_info.value.original_exception, RuntimeError)
    assert str(exc_info.value.original_exception) == f"{hook_attr} boom"
    if secretary is not None:
        assert len(secretary.delivered_memos) == 0


def test_initialization_failure_swallowed_under_default_policy(caplog: pytest.LogCaptureFixture):
    """Under fail_fast=False the default on_error re-raise is logged and the bus continues."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    async def on_init_fail():
        raise RuntimeError("Init failed")

    orchestrator.on_initialize = on_init_fail
    orchestrator.run()

    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None
    assert "Init failed" in caplog.text


def test_orchestrator_on_error_can_handle_initialization_failure():
    """A custom orchestrator on_error can swallow init failures cleanly."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)

    seen: list[OrchestratorHookError] = []

    async def on_init_fail():
        raise RuntimeError("Init failed")

    async def on_error_handle(error: OrchestratorHookError):
        seen.append(error)
        # Return cleanly = handled

    orchestrator.on_initialize = on_init_fail  # type: ignore[method-assign]
    orchestrator.on_error = on_error_handle  # type: ignore[method-assign]

    orchestrator.run()

    assert len(seen) == 1
    assert seen[0].hook_name is HookName.ON_INITIALIZE
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None


def test_finalize_receives_exception_on_process_messages_failure(mocker: MockerFixture):
    """
    Ensure that exceptions raised during message processing (after initialization)
    are passed to the finalize hook, similar to test_initialization_failure.
    """
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    # Mock process_messages to raise an exception
    mocker.patch.object(orchestrator, "process_messages", side_effect=RuntimeError("Process failed"))

    with pytest.raises(RuntimeError, match="Process failed"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert isinstance(orchestrator.finalized_exception, RuntimeError)
    assert str(orchestrator.finalized_exception) == "Process failed"


def test_queue_retrieval_error(orchestrator: MockOrchestrator, mocker: MockerFixture):
    # Patch asyncio.sleep to skip the wait
    mocker.patch("asyncio.sleep")

    call_count = 0

    original_get = orchestrator._queue.get

    async def side_effect() -> BaseMessage:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Queue retrieval failed")
        elif call_count == 2:
            return Memo("recovered")
        return await original_get()

    mocker.patch.object(orchestrator._queue, "get", side_effect=side_effect)

    orchestrator.run()

    # Should have received the recovered message
    assert any(m.id == "recovered" for m in orchestrator.received_messages)


def test_max_timeout_interruption(orchestrator: MockOrchestrator):
    # Set a very short max_timeout
    orchestrator._max_timeout = 0.5
    orchestrator._grace_period = 5.0  # Long grace period

    class SlowProcessor(AsyncProcessor[Memo]):
        def __init__(self, name: str):
            super().__init__(name)
            # Used to validate that the task is cancelled after the timeout happens
            self.cancelled = False

        async def process_message(self, message: Memo):
            try:
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    slow_processor = SlowProcessor("slow_processor")
    orchestrator.register_processor(slow_processor, [Memo])

    orchestrator.submit_message(Memo("slow_memo"))

    with assert_time(0.5, 1.5):
        orchestrator.run()

    assert slow_processor.cancelled

    request = orchestrator.shutdown_request
    assert request is not None
    assert request.kind is ShutdownKind.TIMED_OUT
    assert "max_timeout" in str(request.error)


def test_max_timeout_interruption_preserves_cancellation_reason(orchestrator: MockOrchestrator):
    # A timed-out task's CancelledError should carry the timeout reason, not be
    # silently re-cancelled without a message by the generic shutdown cleanup.
    orchestrator._max_timeout = 0.5
    orchestrator._grace_period = 5.0

    class SlowProcessor(AsyncProcessor[Memo]):
        def __init__(self, name: str):
            super().__init__(name)
            self.cancellation_message: str | None = None

        async def process_message(self, message: Memo):
            try:
                await asyncio.sleep(2.0)
            except asyncio.CancelledError as e:
                self.cancellation_message = str(e)
                raise

    slow_processor = SlowProcessor("slow_processor")
    orchestrator.register_processor(slow_processor, [Memo])

    orchestrator.submit_message(Memo("slow_memo"))

    with assert_time(0.5, 1.5):
        orchestrator.run()

    assert slow_processor.cancellation_message
    assert "max_timeout" in slow_processor.cancellation_message


def test_fatal_processing_error_cancels_task_that_already_swallowed_a_cancellation(
    orchestrator: MockOrchestrator,
):
    # A task that previously caught and suppressed a CancelledError (without calling
    # Task.uncancel()) still has a pending cancellation count. The shutdown cleanup
    # must not treat that as "already being cancelled" and skip it: it should still be
    # cancelled (and stopped) when a sibling processor's FatalProcessingError shuts
    # the bus down.
    class StubbornAnalyst(AsyncProcessor[TaskAssignment]):
        def __init__(self, name: str):
            super().__init__(name)
            self.cancelled_again = False
            self.finished = False

        async def process_message(self, message: TaskAssignment):
            asyncio.current_task().cancel()  # simulate an earlier, unrelated cancellation
            with suppress(asyncio.CancelledError):
                await asyncio.sleep(0)

            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                self.cancelled_again = True
                raise
            self.finished = True

    stubborn = StubbornAnalyst("stubborn")
    orchestrator.register_processor(stubborn, [TaskAssignment])

    original_on_message = orchestrator.on_message_received

    async def on_message_fatal(message: BaseMessage):
        await original_on_message(message)
        if message.id == "fatal_msg":
            raise FatalProcessingError("Fatal error triggered")

    orchestrator.on_message_received = on_message_fatal  # type: ignore[method-assign]

    orchestrator.submit_message(TaskAssignment("stubborn_msg", task_type="slow"))
    orchestrator.submit_message(Memo("fatal_msg"))

    with assert_time(0, 2.0), pytest.raises(FatalProcessingError, match="Fatal error triggered"):
        orchestrator.run()

    assert stubborn.cancelled_again
    assert not stubborn.finished


def test_sync_processor_thread_execution(orchestrator: MockOrchestrator, secretary: Secretary):
    import threading

    class CPUBoundProcessor(SyncProcessor[Announcement]):
        def __init__(self, name: str):
            super().__init__(name)
            self.executed = False
            self.thread_id: int | None = None

        def process_message(self, message: Announcement):
            self.executed = True
            self.thread_id = threading.get_ident()
            time.sleep(0.1)  # Simulate work

    cpu_processor = CPUBoundProcessor("cpu_bound")
    orchestrator.register_processor(cpu_processor, [Announcement])

    orchestrator.submit_message(Announcement("company_announcement"))
    orchestrator.submit_message(Memo("async_memo"))
    orchestrator.run()

    assert cpu_processor.executed
    assert cpu_processor.thread_id is not None

    # Validate it actually run in a different thread than the main loop
    # All async processors are run in the main thread.
    assert cpu_processor.thread_id != threading.get_ident()

    # Verify async processor also ran
    assert len(secretary.delivered_memos) == 1
    assert secretary.delivered_memos[0].id == "async_memo"


class AsyncDelegator(AsyncProcessor[Memo]):
    """Submits a follow-up from the loop thread."""

    async def process_message(self, message: Memo):
        self.submit_message(Announcement(id="delegated", announcement_type="Delegated"))


class SyncDelegator(SyncProcessor[Memo]):
    """Submits a follow-up from an executor thread."""

    def process_message(self, message: Memo):
        self.submit_message(Announcement(id="delegated", announcement_type="Delegated"))


def test_a_worker_thread_submission_is_delivered(analyst: Analyst):
    """A `SyncProcessor` submits from an executor thread, where `asyncio.Queue` can lose the put.

    The real queue loses only the unlucky ones; this one loses every off-loop put, so delivery fails
    deterministically rather than by winning a race.
    """

    class LoseOffLoopPuts(asyncio.Queue):
        """Drops a put made anywhere but the loop thread, the worst case of the real race."""

        def __init__(self, loop_thread: int):
            super().__init__()
            self._loop_thread = loop_thread

        def put_nowait(self, item):
            if threading.get_ident() != self._loop_thread:
                return
            super().put_nowait(item)

    logger = logging.getLogger("test_thread_safe_submit")
    orchestrator = MockOrchestrator(logger, max_timeout=2, grace_period=0.1)
    # `asyncio.run` runs the loop on this thread, so this is the id the queue lets a put through on.
    orchestrator._queue = LoseOffLoopPuts(threading.get_ident())
    orchestrator.register_processor(SyncDelegator("delegator"), [Memo])
    orchestrator.register_processor(analyst, [Announcement])

    orchestrator.submit_message(Memo("delegate_me"))

    orchestrator.run()

    assert [message.id for message in analyst.completed_tasks] == ["delegated"]


@pytest.mark.parametrize("delegator_class", [AsyncDelegator, SyncDelegator], ids=["async", "sync"])
def test_a_processor_submission_survives_a_zero_grace_period(
    analyst: Analyst, delegator_class: type[AsyncDelegator | SyncDelegator]
):
    """A follow-up is queued before the bus can decide it has nothing left to do.

    Every put is now handed to the loop thread, so it happens after `submit_message` returns, and a
    zero grace period stops the bus the moment the queue looks empty. Both kinds of processor are
    covered because the callback that queues the message precedes the task completion that wakes the
    bus by a different route for each.
    """
    logger = logging.getLogger("test_zero_grace_period")
    orchestrator = MockOrchestrator(logger, max_timeout=2, grace_period=0)
    orchestrator.register_processor(delegator_class("delegator"), [Memo])
    orchestrator.register_processor(analyst, [Announcement])

    orchestrator.submit_message(Memo("delegate_me"))

    orchestrator.run()

    assert [message.id for message in analyst.completed_tasks] == ["delegated"]


def test_an_on_initialize_submission_survives_a_zero_grace_period(secretary: Secretary):
    """The bus reads what `on_initialize` submitted, with no grace period to fall back on.

    Nothing awaits between the hook and the bus's first look at the queue, so a put deferred to a loop
    callback would not have happened yet, and a zero grace period stops instead of waiting for it.
    """
    logger = logging.getLogger("test_initialize_submit")
    orchestrator = MockOrchestrator(logger, max_timeout=2, grace_period=0)
    orchestrator.register_processor(secretary, [Memo])

    original_on_initialize = orchestrator.on_initialize

    async def on_initialize_submitting():
        await original_on_initialize()
        orchestrator.submit_message(Memo("from_initialize"))

    orchestrator.on_initialize = on_initialize_submitting  # type: ignore[method-assign]

    orchestrator.run()

    assert [message.id for message in secretary.delivered_memos] == ["from_initialize"]


class SlowGatherer(SyncProcessor[Memo]):
    """Outlives the bus, checking between units of work whether it should stop."""

    def __init__(self, name: str, units: int = 40):
        super().__init__(name)
        self.units = units
        self.units_done = 0
        self.saw_stopping = False

    def process_message(self, message: Memo):
        for _ in range(self.units):
            if self.stopping:
                self.saw_stopping = True
                return
            time.sleep(0.05)
            self.units_done += 1


class UncooperativeGatherer(SyncProcessor[Memo]):
    """Runs to completion whatever the bus is doing, as work that cannot be interrupted does."""

    def __init__(self, name: str, units: int = 30):
        super().__init__(name)
        self.units = units
        self.units_done = 0

    def process_message(self, message: Memo):
        for _ in range(self.units):
            time.sleep(0.05)
            self.units_done += 1


class ShutdownObserver(AsyncProcessor[Memo]):
    def __init__(self, name: str):
        super().__init__(name)
        self.started = asyncio.Event()
        self.notified = False
        self.notified_when_cancelled: bool | None = None

    def on_stop_requested(self) -> None:
        self.notified = True

    async def process_message(self, message: Memo) -> None:
        self.started.set()
        try:
            await asyncio.Future[None]()
        finally:
            self.notified_when_cancelled = self.notified


@pytest.mark.parametrize("lend_executor", [False, True], ids=["own_pool", "borrowed_pool"])
def test_a_sync_processor_outliving_the_timeout_is_waited_for(lend_executor: bool):
    """`on_finalize` must not report while a processor is still mutating what it reports.

    Cancelling the task cannot interrupt a thread, so without waiting the hook publishes a partial
    snapshot and the processor finishes afterwards, once the run has already said what it found.
    A pool lent by the caller runs the same work, so it needs the same wait.
    """
    gatherer = UncooperativeGatherer("gatherer", units=30)
    observed: dict[str, int] = {}

    class Bus(MockOrchestrator):
        async def on_finalize(self, exception: Exception | None):
            await super().on_finalize(exception)
            observed["units_done"] = gatherer.units_done

    with ThreadPoolExecutor(max_workers=2) as lent:
        orchestrator = Bus(
            logging.getLogger("test_drain"),
            max_timeout=0.5,
            grace_period=0.1,
            executor=lent if lend_executor else None,
        )
        orchestrator.register_processor(gatherer, [Memo])
        orchestrator.submit_message(Memo("gather_me"))

        orchestrator.run()

    assert observed["units_done"] == gatherer.units


def test_a_lent_executor_outlives_the_run_that_borrowed_it():
    """The caller may reuse the pool it lent, so the bus must not retire what it does not own.

    Rules out satisfying the wait above by shutting the pool down regardless of ownership.
    """
    gatherer = UncooperativeGatherer("gatherer", units=5)

    with ThreadPoolExecutor(max_workers=2) as lent:
        orchestrator = MockOrchestrator(
            logging.getLogger("test_lent_pool"), max_timeout=0.5, grace_period=0.1, executor=lent
        )
        orchestrator.register_processor(gatherer, [Memo])
        orchestrator.submit_message(Memo("gather_me"))

        orchestrator.run()

        assert lent.submit(str, "still usable").result() == "still usable"


def test_a_sync_processor_can_abandon_work_once_the_bus_stops():
    """The stop flag is what makes a timeout bound a sync processor at all.

    Without it the processor runs all its units however long the bus has been gone, which is the
    difference between a run that overshoots by one unit of work and one that overshoots by a batch.
    """
    gatherer = SlowGatherer("gatherer", units=200)
    orchestrator = MockOrchestrator(logging.getLogger("test_stopping"), max_timeout=0.3, grace_period=0.1)
    orchestrator.register_processor(gatherer, [Memo])
    orchestrator.submit_message(Memo("gather_me"))

    orchestrator.run()

    assert gatherer.saw_stopping
    assert gatherer.units_done < gatherer.units


def test_a_caller_provided_executor_outlives_the_bus():
    """A caller that supplies an executor may reuse it, so the bus must not retire it."""
    executor = ThreadPoolExecutor(max_workers=1)
    orchestrator = MockOrchestrator(logging.getLogger("test_borrowed"), executor=executor, grace_period=0.1)
    orchestrator.register_processor(Secretary("secretary"), [Memo])
    orchestrator.submit_message(Memo("memo"))

    orchestrator.run()

    assert executor.submit(lambda: "still usable").result() == "still usable"
    executor.shutdown(wait=True)


def test_processor_submit_without_bus():
    processor = Secretary("orphan")
    with pytest.raises(ProcessorQueueError, match="This processor has not been added"):
        processor.submit_message(Memo("fail"))


def test_fatal_processing_error_stops_orchestrator(orchestrator: MockOrchestrator):
    # Capture the original method to preserve its behavior (tracking received messages)
    original_on_message = orchestrator.on_message_received

    async def on_message_fatal(message: BaseMessage):
        await original_on_message(message)
        if message.id == "fatal_msg":
            raise FatalProcessingError("Fatal error triggered")

    # Monkey patch the instance method
    orchestrator.on_message_received = on_message_fatal  # type: ignore

    orchestrator.submit_message(Memo("fatal_msg"))
    orchestrator.submit_message(Memo("ignored_msg"))

    with pytest.raises(FatalProcessingError, match="Fatal error triggered"):
        orchestrator.run()

    # Finalize ran with the fatal error attached
    assert "finalize" in orchestrator.events
    assert isinstance(orchestrator.finalized_exception, FatalProcessingError)

    # Only the first message was processed/received by the hook
    assert len(orchestrator.received_messages) == 1
    assert orchestrator.received_messages[0].id == "fatal_msg"

    request = orchestrator.shutdown_request
    assert request is not None
    assert request.kind is ShutdownKind.FAILED
    assert request.error is orchestrator.finalized_exception


class FatalRequester(AsyncProcessor[Memo]):
    """Stops the bus with a failure directly, the way a processor that decides to can."""

    async def process_message(self, message: Memo):
        assert self.bus is not None
        self.bus.request_shutdown(ShutdownRequest.failed(RuntimeError("the run is doomed")))


def test_an_explicit_failed_request_propagates_its_error_through_finalization():
    """An explicit failed request reaches both finalization and the caller."""
    orchestrator = MockOrchestrator(logging.getLogger("test_failed_request"), grace_period=0.1)
    orchestrator.register_processor(FatalRequester("requester"), [Memo])
    orchestrator.submit_message(Memo("doomed"))

    with pytest.raises(RuntimeError, match="the run is doomed"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert isinstance(orchestrator.finalized_exception, RuntimeError)
    request = orchestrator.shutdown_request
    assert request is not None
    assert request.kind is ShutdownKind.FAILED
    assert request.error is orchestrator.finalized_exception


def test_a_failed_request_answers_the_run_even_when_another_error_escapes_after_it():
    """A later exception cannot replace the failure reported to finalization and the caller."""
    orchestrator = MockOrchestrator(logging.getLogger("test_first_failure"), grace_period=0.1)

    original = ValueError("original failure")

    async def on_initialize_records_then_fails() -> None:
        orchestrator.request_shutdown(ShutdownRequest.failed(original))
        raise FatalProcessingError("later failure")

    orchestrator.on_initialize = on_initialize_records_then_fails  # type: ignore[method-assign]

    with pytest.raises(ValueError, match="original failure"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is original
    request = orchestrator.shutdown_request
    assert request is not None
    assert request.kind is ShutdownKind.FAILED
    assert request.error is original


class FailureRequester(AsyncProcessor[Memo]):
    """Request failure from an active processor."""

    def __init__(self, name: str, bus: FirstFailureBus) -> None:
        super().__init__(name)
        self.failure_bus = bus

    async def process_message(self, message: Memo) -> None:
        self.failure_bus.request_shutdown(ShutdownRequest.failed(self.failure_bus.original))
        self.failure_bus.at_phase.set()
        await asyncio.Future[None]()


class FirstFailureBus(MockOrchestrator):
    """Control when failure and interruption occur during a run."""

    def __init__(self, phase: str, *, record_failure: bool = True, phase_error: Exception | None = None):
        super().__init__(
            logging.getLogger("test_first_failure_lifecycle"),
            max_timeout=5,
            grace_period=0.1,
            fail_fast=phase == "finalizer error" or phase_error is not None,
        )
        self.phase = phase
        self.record_failure = record_failure
        self.phase_error = phase_error
        self.original = ValueError("original failure")
        self.at_phase = asyncio.Event()
        self.proceed = asyncio.Event()
        self.finalize_calls: list[Exception | None] = []

    async def on_initialize(self) -> None:
        if self.phase == "processing":
            self.submit_message(Memo("doomed"))
        elif self.record_failure:
            self.request_shutdown(ShutdownRequest.failed(self.original))

    async def _drain_executor(self) -> None:
        if self.phase == "draining":
            self.at_phase.set()
            await self.proceed.wait()
            if self.phase_error is not None:
                raise self.phase_error
        await super()._drain_executor()

    async def on_finalize(self, exception: Exception | None) -> None:
        self.finalize_calls.append(exception)
        if self.phase == "finalization":
            self.at_phase.set()
            await self.proceed.wait()
            if self.phase_error is not None:
                raise self.phase_error
        if self.phase == "finalizer error":
            raise RuntimeError("secondary finalization failure")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("phase", "hook_reached", "expected_note"),
    [
        pytest.param("processing", True, "CancelledError", id="processing_cancellation"),
        pytest.param("draining", False, "CancelledError", id="drain_cancellation"),
        pytest.param("finalization", True, "CancelledError", id="finalization_cancellation"),
        pytest.param("finalizer error", True, "secondary finalization failure", id="finalizer_error"),
    ],
)
async def test_recorded_failure_survives_secondary_errors(
    phase: str,
    hook_reached: bool,
    expected_note: str,
    caplog: pytest.LogCaptureFixture,
):
    """The accepted failure reaches the caller unchanged, whatever goes wrong after it."""
    bus = FirstFailureBus(phase)
    if phase == "processing":
        bus.register_processor(FailureRequester("requester", bus), [Memo])

    run = asyncio.create_task(bus._entry_point())
    try:
        if phase != "finalizer error":
            await asyncio.wait_for(bus.at_phase.wait(), timeout=2)
            run.cancel("the owner stopped waiting")
        done, _ = await asyncio.wait({run}, timeout=2)
        assert done, "The interrupted run did not finish"
        with pytest.raises(ValueError, match="original failure") as exc_info:
            await run
    finally:
        bus.proceed.set()
        run.cancel()
        await asyncio.gather(run, return_exceptions=True)

    assert exc_info.value is bus.original
    assert bus.finalize_calls == ([bus.original] if hook_reached else [])
    context = "message processing" if phase == "processing" else "finalization"
    assert any(
        note.startswith(f"Additional exception during {context}:") and expected_note in note
        for note in getattr(exc_info.value, "__notes__", [])
    )
    assert f"Secondary exception during {context}:" in caplog.text
    assert expected_note in caplog.text
    assert "Traceback (most recent call last)" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["draining", "finalization"])
@pytest.mark.parametrize("completion", ["return", "cancel", "error"])
async def test_a_failed_request_accepted_during_finalization_is_preserved(phase: str, completion: str):
    """A late failed request must survive both normal completion and further cleanup failures."""
    secondary = RuntimeError("secondary phase failure") if completion == "error" else None
    bus = FirstFailureBus(phase, record_failure=False, phase_error=secondary)
    run = asyncio.create_task(bus._entry_point())
    try:
        await asyncio.wait_for(bus.at_phase.wait(), timeout=2)
        bus.request_shutdown(ShutdownRequest.failed(bus.original))
        if completion == "cancel":
            run.cancel("cleanup interrupted")
        else:
            bus.proceed.set()
        done, _ = await asyncio.wait({run}, timeout=2)
        assert done, "The run did not finish after the failed request"
        with pytest.raises(ValueError, match="original failure") as exc_info:
            await run
    finally:
        bus.proceed.set()
        run.cancel()
        await asyncio.gather(run, return_exceptions=True)

    assert exc_info.value is bus.original
    if phase == "draining":
        assert bus.finalize_calls == ([bus.original] if completion == "return" else [])
    else:
        assert bus.finalize_calls == [None]
    if completion != "return":
        diagnostic = "CancelledError" if completion == "cancel" else "secondary phase failure"
        assert any(diagnostic in note for note in getattr(bus.original, "__notes__", []))


@pytest.mark.parametrize("fail_fast", [False, True])
def test_executor_drain_errors_propagate_without_running_the_finalization_hook(fail_fast: bool):
    """Executor failures must not be swallowed or reclassified as hook failures."""
    original = RuntimeError("executor shutdown failed")

    class Bus(MockOrchestrator):
        async def _drain_executor(self) -> None:
            raise original

    bus = Bus(logging.getLogger("test_drain_error"), grace_period=0, fail_fast=fail_fast)
    with pytest.raises(RuntimeError) as exc_info:
        bus.run()

    assert exc_info.value is original
    assert bus.events == ["initialize"]


def test_reraising_the_primary_failure_does_not_add_a_secondary_failure():
    """Reporting the same failure twice must not invent an additional failure."""
    original = FatalProcessingError("original failure")

    class Bus(MockOrchestrator):
        async def on_initialize(self) -> None:
            self.request_shutdown(ShutdownRequest.failed(original))

        async def on_finalize(self, exception: Exception | None) -> None:
            assert exception is original
            raise original

    bus = Bus(logging.getLogger("test_repeated_primary"), grace_period=0)
    with pytest.raises(FatalProcessingError) as exc_info:
        bus.run()

    assert exc_info.value is original
    assert getattr(original, "__notes__", []) == []


@pytest.mark.asyncio
async def test_cancelled_hook_cleanup_errors_are_retained_with_the_primary_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """An unexpected error during hook cancellation must remain available for diagnosis."""
    monkeypatch.setattr("ddev.event_bus.orchestrator.STOP_CHECK_INTERVAL", 0.005)
    original = ValueError("original failure")

    class Bus(MockOrchestrator):
        async def on_initialize(self) -> None:
            self.request_shutdown(ShutdownRequest.failed(original))
            try:
                await asyncio.Future[None]()
            finally:
                raise RuntimeError("hook cleanup failed")

    bus = Bus(logging.getLogger("test_hook_cleanup_error"), grace_period=0)
    run = asyncio.create_task(bus._entry_point())
    try:
        done, _ = await asyncio.wait({run}, timeout=2)
        assert done, "The cancelled hook did not finish"
        with pytest.raises(ValueError) as exc_info:
            await run
        assert exc_info.value is original
        assert any(
            note.startswith("Additional exception during on_initialize cleanup:") and "hook cleanup failed" in note
            for note in getattr(original, "__notes__", [])
        )
        assert "Secondary exception during on_initialize cleanup:" in caplog.text
    finally:
        run.cancel()
        await asyncio.gather(run, return_exceptions=True)


def test_finalization_failure_retains_an_earlier_cancellation(caplog: pytest.LogCaptureFixture):
    """A fatal cleanup error must retain the cancellation that preceded it."""
    cancellation = asyncio.CancelledError("owner interrupted")
    failure = FatalProcessingError("cleanup failed")

    class Bus(MockOrchestrator):
        async def on_initialize(self) -> None:
            raise cancellation

        async def on_finalize(self, exception: Exception | None) -> None:
            raise failure

    bus = Bus(logging.getLogger("test_cancel_then_cleanup_error"), grace_period=0)
    with pytest.raises(FatalProcessingError) as exc_info:
        bus.run()

    assert exc_info.value is failure
    assert any(
        note.startswith("Additional exception during initialization:") and "owner interrupted" in note
        for note in getattr(failure, "__notes__", [])
    )
    assert "Secondary exception during initialization:" in caplog.text
    assert "owner interrupted" in caplog.text
    assert "Traceback (most recent call last)" in caplog.text


def test_primary_failure_keeps_its_exception_chain(
    caplog: pytest.LogCaptureFixture,
):
    """The caller sees the recorded failure with its cause and context intact, plus the later error."""
    context_error = ValueError("what was being handled when it failed")
    implicit_context = KeyError("the implicit context")
    cause_error = ValueError("the explicit cause")

    def raise_chained_failure() -> None:
        try:
            raise context_error
        except ValueError:
            try:
                raise implicit_context
            except KeyError:
                raise RuntimeError("original failure") from cause_error

    original: Exception
    try:
        raise_chained_failure()
    except RuntimeError as caught:
        original = caught

    orchestrator = MockOrchestrator(logging.getLogger("test_first_failure_chains"), grace_period=0.1, fail_fast=True)

    async def on_initialize_records_then_fails() -> None:
        orchestrator.request_shutdown(ShutdownRequest.failed(original))
        raise FatalProcessingError("later failure")

    orchestrator.on_initialize = on_initialize_records_then_fails  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="original failure") as exc_info:
        orchestrator.run()

    assert exc_info.value is original
    assert exc_info.value.__cause__ is cause_error
    assert exc_info.value.__context__ is implicit_context
    assert any(
        note.startswith("Additional exception during initialization:") and "later failure" in note
        for note in getattr(exc_info.value, "__notes__", [])
    )
    assert "Secondary exception during initialization:" in caplog.text
    assert "later failure" in caplog.text
    assert "Traceback (most recent call last)" in caplog.text


@pytest.mark.parametrize(
    "hook_attr",
    ["on_initialize", "on_message_received"],
    ids=["from_initialize", "from_message_loop"],
)
def test_a_cancellation_escaping_the_bus_is_recorded_and_propagated(hook_attr: str):
    """Escaping cancellation triggers stop notifications without changing its propagation."""
    orchestrator = MockOrchestrator(logging.getLogger(f"test_cancelled_{hook_attr}"), grace_period=0.1)
    watcher = StopWatcher("watcher")
    orchestrator.register_processor(watcher, [TaskAssignment])

    async def escape(*args: object) -> None:
        raise asyncio.CancelledError("owner cancelled the bus")

    setattr(orchestrator, hook_attr, escape)

    if hook_attr == "on_message_received":
        orchestrator.submit_message(Memo("cancel_me"))

    with pytest.raises(asyncio.CancelledError, match="owner cancelled the bus"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert watcher.stop_notifications == 1
    request = orchestrator.shutdown_request
    assert request is not None
    assert request.kind is ShutdownKind.CANCELLED


@pytest.mark.parametrize("kind", [ShutdownKind.FAILED, ShutdownKind.TIMED_OUT], ids=["fatal", "timeout"])
def test_a_terminal_exit_notifies_the_worker_before_cancelling_it(kind: ShutdownKind, monkeypatch: pytest.MonkeyPatch):
    """Processors receive their stop notification before cancellation starts their cleanup."""
    worker = ShutdownObserver("worker")
    orchestrator = MockOrchestrator(logging.getLogger("test_terminal_notify"), max_timeout=30, grace_period=0)

    async def on_message_received(message: BaseMessage) -> None:
        if kind is ShutdownKind.TIMED_OUT:
            loop = asyncio.get_running_loop()
            real_time = loop.time

            def deadline_clock() -> float:
                return real_time() + (60 if worker.started.is_set() else 0)

            # Expire the deadline only after the worker has started.
            monkeypatch.setattr(loop, "time", deadline_clock)
        elif message.id == "fatal_msg":
            async with asyncio.timeout(2):
                await worker.started.wait()
            raise FatalProcessingError("fatal error triggered")

    orchestrator.on_message_received = on_message_received  # type: ignore[method-assign]
    orchestrator.register_processor(worker, [Memo])
    orchestrator.submit_message(Memo("observe_shutdown"))
    if kind is ShutdownKind.FAILED:
        orchestrator.submit_message(Memo("fatal_msg"))

    expectation = (
        pytest.raises(FatalProcessingError, match="fatal error triggered")
        if kind is ShutdownKind.FAILED
        else does_not_raise()
    )
    with expectation:
        orchestrator.run()

    assert worker.notified_when_cancelled is True
    request = orchestrator.shutdown_request
    assert request is not None
    assert request.kind is kind


def test_the_first_shutdown_request_wins_and_is_never_superseded():
    """Later failures or cancellation requests cannot replace the cause or repeat notifications."""
    watcher = StopWatcher("watcher")
    orchestrator = MockOrchestrator(logging.getLogger("test_shutdown_latch"), max_timeout=30, grace_period=1)
    orchestrator.register_processor(watcher, [TaskAssignment])

    original = RuntimeError("the original failure")
    assert orchestrator.request_shutdown(ShutdownRequest.failed(original))
    assert not orchestrator.request_shutdown(ShutdownRequest.failed(RuntimeError("a later failure")))
    assert not orchestrator.request_shutdown(ShutdownRequest.cancelled())

    request = orchestrator.shutdown_request
    assert request is not None
    assert request.kind is ShutdownKind.FAILED
    assert request.error is original
    # Only the winner notifies, so the losing requests cannot repeat the stop notification.
    assert watcher.stop_notifications == 1


def test_orchestrator_hook_failure_swallowed_under_default_policy(
    secretary: Secretary, caplog: pytest.LogCaptureFixture
):
    """Under fail_fast=False, an orchestrator hook failure is logged and processing continues."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)
    orchestrator.register_processor(secretary, [Memo])

    call_count = [0]

    async def on_message_first_fails(message: BaseMessage):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("first message hook failed")

    orchestrator.on_message_received = on_message_first_fails  # type: ignore[method-assign]

    orchestrator.submit_message(Memo("boom_msg"))
    orchestrator.submit_message(Memo("ok_msg"))
    orchestrator.run()

    assert orchestrator.finalized_exception is None
    assert "first message hook failed" in caplog.text
    # Both messages were dispatched: hook error didn't stop the loop
    assert len(secretary.delivered_memos) == 2


def test_processor_on_error_can_signal_fatal(orchestrator: MockOrchestrator, secretary: Secretary):
    """on_error raising FatalProcessingError stops the bus regardless of fail_fast."""

    async def fatal_on_error(error: Exception):
        raise FatalProcessingError("on_error decided to stop the bus")

    secretary.on_error = fatal_on_error  # type: ignore[method-assign]

    orchestrator.submit_message(Memo("trigger_fatal", content="fail_processing"))

    with pytest.raises(FatalProcessingError, match="on_error decided to stop the bus"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert isinstance(orchestrator.finalized_exception, FatalProcessingError)
    assert len(secretary.delivered_memos) == 0


def test_finalize_failure_swallowed_under_default_policy(caplog: pytest.LogCaptureFixture):
    """Under fail_fast=False on_finalize failures route through on_error and are absorbed."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    async def on_finalize_boom(exception: Exception | None):
        orchestrator.events.append("finalize")
        raise RuntimeError("finalize boom")

    orchestrator.on_finalize = on_finalize_boom  # type: ignore[method-assign]

    orchestrator.run()

    assert "finalize" in orchestrator.events
    assert "finalize boom" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fail_fast", "waiting_recovery"),
    [(False, False), (True, False), (False, True)],
    ids=["default-policy", "fail-fast", "interrupted-recovery"],
)
async def test_recorded_failure_keeps_secondary_finalization_diagnostics(
    caplog: pytest.LogCaptureFixture, fail_fast: bool, waiting_recovery: bool
):
    """An accepted failure retains cleanup errors after failed or interrupted recovery."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=fail_fast)

    saw_exception: list[Exception | None] = []

    original = RuntimeError("init failed")

    async def on_init_fail() -> None:
        if fail_fast:
            raise original
        orchestrator.request_shutdown(ShutdownRequest.failed(OrchestratorHookError(HookName.ON_INITIALIZE, original)))

    async def on_finalize_boom(exception: Exception | None):
        orchestrator.events.append("finalize")
        saw_exception.append(exception)
        raise RuntimeError("finalize boom")

    orchestrator.on_initialize = on_init_fail  # type: ignore[method-assign]
    orchestrator.on_finalize = on_finalize_boom  # type: ignore[method-assign]
    if waiting_recovery:

        async def on_error(error: OrchestratorHookError) -> None:
            await asyncio.Future[None]()

        orchestrator.on_error = on_error  # type: ignore[method-assign]

    run = asyncio.create_task(orchestrator._entry_point())
    try:
        done, _ = await asyncio.wait({run}, timeout=2)
        assert done, "Error recovery prevented shutdown"
        with pytest.raises(OrchestratorHookError) as exc_info:
            await run
    finally:
        run.cancel()
        await asyncio.gather(run, return_exceptions=True)

    assert exc_info.value.hook_name is HookName.ON_INITIALIZE
    assert exc_info.value.original_exception is original
    assert saw_exception == [exc_info.value]
    context = "finalization" if fail_fast else "on_error handling on_finalize"
    assert any(
        note.startswith(f"Additional exception during {context}:") and "finalize boom" in note
        for note in getattr(exc_info.value, "__notes__", [])
    )
    assert f"Secondary exception during {context}:" in caplog.text
    assert "finalize boom" in caplog.text
    assert "Traceback (most recent call last)" in caplog.text


def test_skip_message_error_from_on_message_received(
    orchestrator: MockOrchestrator, secretary: Secretary, caplog: pytest.LogCaptureFixture
):
    """SkipMessageError from on_message_received skips dispatch and continues with the next message."""

    async def on_message_skip_first(message: BaseMessage):
        if message.id == "skip_me":
            raise SkipMessageError("not safe to process")

    orchestrator.on_message_received = on_message_skip_first  # type: ignore[method-assign]

    orchestrator.submit_message(Memo("skip_me"))
    orchestrator.submit_message(Memo("ok_msg"))
    orchestrator.run()

    assert orchestrator.finalized_exception is None
    assert [m.id for m in secretary.delivered_memos] == ["ok_msg"]
    assert "Skipping message skip_me" in caplog.text
    assert "not safe to process" in caplog.text


def test_skip_message_error_outside_on_message_received_has_no_special_behavior(
    bare_orchestrator: MockOrchestrator, caplog: pytest.LogCaptureFixture
):
    """SkipMessageError raised in processor scope has no special skip behavior."""

    class SkipperProcessor(AsyncProcessor[Memo]):
        def __init__(self, name: str):
            super().__init__(name)
            self.attempts: list[Memo] = []

        async def process_message(self, message: Memo):
            self.attempts.append(message)
            raise SkipMessageError("skip from processor scope")

    proc = SkipperProcessor("skipper")
    bare_orchestrator.register_processor(proc, [Memo])

    bare_orchestrator.submit_message(Memo("m1"))
    bare_orchestrator.submit_message(Memo("m2"))
    bare_orchestrator.run()

    # process_message was attempted for both messages — bus did not short-circuit
    assert len(proc.attempts) == 2
    # No "Skipping message" log line — that path is reserved for on_message_received context
    assert "Skipping message" not in caplog.text


def test_should_process_message_conditional_filtering(bare_orchestrator: MockOrchestrator):
    """Processor processes only messages matching a custom predicate on message attributes."""

    class HighPriorityAnalyst(AsyncProcessor[TaskAssignment]):
        def __init__(self, name: str, min_priority: int):
            super().__init__(name)
            self.min_priority = min_priority
            self.processed: list[TaskAssignment] = []

        def should_process_message(self, message: BaseMessage) -> bool:
            return isinstance(message, TaskAssignment) and message.priority >= self.min_priority

        async def process_message(self, message: TaskAssignment):
            self.processed.append(message)

    analyst = HighPriorityAnalyst("high_priority_analyst", min_priority=10)
    bare_orchestrator.register_processor(analyst, [TaskAssignment])

    bare_orchestrator.submit_message(TaskAssignment("low_task", priority=1))
    bare_orchestrator.submit_message(TaskAssignment("high_task", priority=100))
    bare_orchestrator.run()

    assert len(analyst.processed) == 1
    assert analyst.processed[0].id == "high_task"


def test_should_process_message_is_independent_per_processor(bare_orchestrator: MockOrchestrator, secretary: Secretary):
    """Each processor filters independently — one skipping a message does not affect the others."""

    class UrgentMemosOnlyProcessor(AsyncProcessor[Memo]):
        def __init__(self, name: str):
            super().__init__(name)
            self.processed: list[Memo] = []

        def should_process_message(self, message: BaseMessage) -> bool:
            return isinstance(message, Memo) and message.subject == "urgent"

        async def process_message(self, message: Memo):
            self.processed.append(message)

    urgent_proc = UrgentMemosOnlyProcessor("urgent_only")
    bare_orchestrator.register_processor(secretary, [Memo])
    bare_orchestrator.register_processor(urgent_proc, [Memo])

    bare_orchestrator.submit_message(Memo("memo1", subject="regular"))
    bare_orchestrator.submit_message(Memo("memo2", subject="urgent"))
    bare_orchestrator.run()

    assert len(secretary.delivered_memos) == 2
    assert len(urgent_proc.processed) == 1
    assert urgent_proc.processed[0].id == "memo2"


def brief_work(message: BaseMessage) -> None:
    time.sleep(0.001)


async def test_pending_sync_work_can_be_read_while_workers_finish_underneath_it():
    """Each future's done callback discards on the worker thread that ran it, racing this snapshot.

    Read straight off the live set, CPython raises `Set changed size during iteration`. That lands in
    `_drain_executor`, which runs before the `try` around `on_finalize`, so the hook and every
    error-policy path with it would be skipped.
    """
    with ThreadPoolExecutor(max_workers=16) as lent:
        orchestrator = MockOrchestrator(logging.getLogger("test_sync_work"), executor=lent)
        running = [
            asyncio.create_task(orchestrator._run_in_worker(brief_work, Memo(id=str(index)))) for index in range(200)
        ]
        await asyncio.sleep(0)

        for _ in range(500):
            orchestrator._pending_sync_work()

        await asyncio.gather(*running)

    assert orchestrator._pending_sync_work() == set()


class StopRequester(AsyncProcessor[Memo]):
    """Asks the bus to stop from inside a processor, then submits as the runner's `finally` does."""

    def __init__(self, name: str):
        super().__init__(name)
        self.processed: list[Memo] = []

    async def process_message(self, message: Memo):
        self.processed.append(message)
        assert self.bus is not None
        self.bus.request_shutdown(ShutdownRequest.cancelled())
        self.submit_message(Memo("after_stop", subject="late"))


class Signaller(AsyncProcessor[Memo]):
    """Sends the process a real signal while the bus is running."""

    def __init__(self, name: str, send: signal.Signals):
        super().__init__(name)
        self._send = send
        self.stop_notifications = 0

    async def process_message(self, message: Memo):
        os.kill(os.getpid(), self._send)

    def on_stop_requested(self):
        self.stop_notifications += 1


class StopWatcher(AsyncProcessor[TaskAssignment | Announcement]):
    def __init__(self, name: str, *, fail: bool = False):
        super().__init__(name)
        self.stop_notifications = 0
        self._fail = fail

    async def process_message(self, message: TaskAssignment | Announcement):
        pass

    def on_stop_requested(self):
        self.stop_notifications += 1
        if self._fail:
            raise RuntimeError("this processor cannot wind down")


@pytest.mark.parametrize(
    "registrations",
    [
        pytest.param([[TaskAssignment, Announcement]], id="one-call-two-types"),
        pytest.param([[TaskAssignment], [Announcement]], id="two-calls"),
    ],
)
def test_a_processor_is_told_once_however_often_it_subscribed(registrations: list[list[type[BaseMessage]]]):
    """Subscriptions are per message type, so notifying per subscription would repeat the hook."""
    watcher = StopWatcher("watcher")
    orchestrator = MockOrchestrator(logging.getLogger("test_stop_hook_once"), max_timeout=30, grace_period=1)
    for message_types in registrations:
        orchestrator.register_processor(watcher, message_types)

    orchestrator.request_shutdown(ShutdownRequest.cancelled())

    assert watcher.stop_notifications == 1


def test_asking_to_stop_again_notifies_nobody_and_does_not_block():
    """The claim is a latch that is never released, so a second call must test it rather than wait."""
    watcher = StopWatcher("watcher")
    orchestrator = MockOrchestrator(logging.getLogger("test_stop_repeat"), max_timeout=30, grace_period=1)
    orchestrator.register_processor(watcher, [TaskAssignment])

    orchestrator.request_shutdown(ShutdownRequest.cancelled())
    orchestrator.request_shutdown(ShutdownRequest.cancelled())

    assert watcher.stop_notifications == 1


requires_signals = pytest.mark.skipif(sys.platform == "win32", reason="Windows loops cannot install these")


@contextmanager
def caught_rather_than_fatal(sent: signal.Signals) -> Generator[list[signal.Signals]]:
    """Record *sent* instead of letting its default action end the process.

    A bus that stopped installing handlers would otherwise kill the test session rather than fail a
    test: SIGTERM's default is death, and nothing can catch that.
    """
    reached_the_process: list[signal.Signals] = []
    previous = signal.signal(sent, lambda *_: reached_the_process.append(sent))
    try:
        yield reached_the_process
    finally:
        signal.signal(sent, previous)


@requires_signals
@pytest.mark.parametrize(
    ("sent", "propagate", "expectation"),
    [
        pytest.param(signal.SIGINT, True, pytest.raises(KeyboardInterrupt), id="sigint-propagates"),
        pytest.param(signal.SIGINT, False, does_not_raise(), id="sigint-suppressed"),
        # Nothing in the interpreter raises for SIGTERM, so there is nothing to hand back.
        pytest.param(signal.SIGTERM, True, does_not_raise(), id="sigterm-has-no-exception"),
    ],
)
def test_an_interrupted_run_hands_the_interrupt_back_once_it_has_wound_down(
    sent: signal.Signals, propagate: bool, expectation: AbstractContextManager
):
    """Handling SIGINT is what stops `KeyboardInterrupt` reaching the caller, and with it whatever the
    caller does about one: Click turns it into `Aborted!` and exit 1, so a caller that wants that back
    asks for it here.

    Raised after the wind-down rather than instead of it, so the cleanup still happens first.
    """
    signaller = Signaller("signaller", sent)
    orchestrator = MockOrchestrator(logging.getLogger("test_interrupt_propagation"), max_timeout=30, grace_period=1)
    orchestrator.register_processor(signaller, [Memo])
    orchestrator.submit_message(Memo("memo1"))

    with caught_rather_than_fatal(sent), expectation:
        orchestrator.run(propagate_keyboard_interrupt=propagate)

    # Whatever the caller sees, the bus wound down first rather than being cut short.
    assert orchestrator.stopping
    assert signaller.stop_notifications == 1


@pytest.mark.asyncio
@requires_signals
async def test_an_interrupted_drain_still_hands_the_signal_handlers_back():
    """Draining can be interrupted, but the run still restores the handlers it displaced."""

    def caller_handler(signum: int, frame: FrameType | None) -> None: ...

    previous = signal.signal(signal.SIGTERM, caller_handler)
    try:
        bus = FirstFailureBus("draining")
        run = asyncio.create_task(bus._entry_point())
        try:
            await asyncio.wait_for(bus.at_phase.wait(), timeout=2)
            run.cancel("the owner stopped waiting")
            done, _ = await asyncio.wait({run}, timeout=2)
            assert done, "The interrupted drain did not finish"
            with pytest.raises(ValueError, match="original failure"):
                await run
        finally:
            bus.proceed.set()
            run.cancel()
            await asyncio.gather(run, return_exceptions=True)

        assert signal.getsignal(signal.SIGTERM) is caller_handler
    finally:
        signal.signal(signal.SIGTERM, previous)


@requires_signals
@pytest.mark.parametrize("sent", [signal.SIGINT, signal.SIGTERM], ids=lambda s: s.name)
def test_a_run_gives_back_the_handler_it_displaced(sent: signal.Signals):
    """Nothing says the bus owns the process: a caller may have its own handler and outlive the run.

    `remove_signal_handler` restores the interpreter default rather than what was displaced, so without
    putting it back the caller silently loses its handler to a run that ended normally.
    """

    def caller_handler(signum: int, frame: FrameType | None) -> None: ...

    orchestrator = MockOrchestrator(logging.getLogger("test_signal_restore"), max_timeout=30, grace_period=0)
    orchestrator.register_processor(Secretary("secretary"), [Memo])
    previous = signal.signal(sent, caller_handler)
    try:
        orchestrator.run()

        assert signal.getsignal(sent) is caller_handler
    finally:
        signal.signal(sent, previous)


@requires_signals
@pytest.mark.parametrize("sent", [signal.SIGINT, signal.SIGTERM], ids=lambda s: s.name)
def test_a_signal_reaches_the_bus_rather_than_the_process(sent: signal.Signals):
    """Both defaults end a run, differently: SIGINT raises `KeyboardInterrupt` where it lands and
    SIGTERM kills outright, so the fallback keeps a regression reportable rather than fatal.

    The bus having handled the signal is what leaves that fallback untouched.
    """
    signaller = Signaller("signaller", sent)
    orchestrator = MockOrchestrator(logging.getLogger("test_signal_stop"), max_timeout=30, grace_period=1)
    orchestrator.register_processor(signaller, [Memo])
    orchestrator.submit_message(Memo("memo1"))

    with caught_rather_than_fatal(sent) as reached_the_process:
        orchestrator.run()

    assert reached_the_process == []
    assert orchestrator.stopping
    assert signaller.stop_notifications == 1


def test_a_stop_is_not_derailed_by_a_processor_that_fails_to_wind_down():
    """A signal handler is a valid caller, and there an escaping exception loses the stop itself."""
    failing = StopWatcher("failing", fail=True)
    watcher = StopWatcher("watcher")
    orchestrator = MockOrchestrator(logging.getLogger("test_stop_hook_failure"), max_timeout=30, grace_period=1)
    orchestrator.register_processor(failing, [TaskAssignment])
    orchestrator.register_processor(watcher, [Announcement])

    orchestrator.request_shutdown(ShutdownRequest.cancelled())

    assert orchestrator.stopping
    assert watcher.stop_notifications == 1


def test_a_requested_stop_ends_an_idle_bus_without_waiting_out_the_grace_period(
    secretary: Secretary, caplog: pytest.LogCaptureFixture
):
    """A caller under a deadline it does not control cannot afford the grace period.

    The dispatcher's default grace is 30s against the ~10s a cancelled CI job gets, so a stop that
    lands while the bus sits idle has to interrupt that wait rather than be seen once it expires.
    """
    grace_period = 10.0
    orchestrator = MockOrchestrator(
        logging.getLogger("test_request_shutdown"), max_timeout=60, grace_period=grace_period
    )
    orchestrator.register_processor(secretary, [Memo])
    orchestrator.submit_message(Memo("memo1"))
    # From a thread, and only once the bus is already idle inside the grace wait.
    threading.Timer(0.3, orchestrator.request_shutdown, args=(ShutdownRequest.cancelled(),)).start()

    start = time.perf_counter()
    with caplog.at_level(logging.INFO):
        orchestrator.run()
    elapsed = time.perf_counter() - start

    assert elapsed < grace_period / 2
    assert "finalize" in orchestrator.events
    # Said at the exit, or this reads in the logs like the grace period expiring on its own.
    assert "Stopping on request while idle." in caplog.text


def test_work_submitted_after_a_stop_request_is_reported_rather_than_lost(
    secretary: Secretary, caplog: pytest.LogCaptureFixture
):
    """A stopping bus exits before draining its queue, so a late put is never read by anyone.

    Processors submit follow-up work from `finally` blocks, and without refusing it at the door that
    work disappears with nothing in the log to say the run dropped it.
    """
    requester = StopRequester("requester")
    orchestrator = MockOrchestrator(logging.getLogger("test_stop_guard"), max_timeout=30, grace_period=1)
    orchestrator.register_processor(requester, [Memo])
    orchestrator.register_processor(secretary, [Memo])

    orchestrator.submit_message(Memo("memo1"))
    with caplog.at_level(logging.WARNING):
        orchestrator.run()

    assert [message.id for message in requester.processed] == ["memo1"]
    assert "Dropped Memo(after_stop)" in caplog.text


def test_a_processor_is_not_dispatched_to_after_a_stop_request(secretary: Secretary):
    """Both processors' tasks are created together, so the second is scheduled after the stop.

    Refusing centrally is what makes that hold for every processor, including ones that never learn
    to check the flag themselves.
    """
    requester = StopRequester("requester")
    orchestrator = MockOrchestrator(logging.getLogger("test_dispatch_guard"), max_timeout=30, grace_period=1)
    orchestrator.register_processor(requester, [Memo])
    orchestrator.register_processor(secretary, [Memo])

    orchestrator.submit_message(Memo("memo1"))
    orchestrator.run()

    assert [message.id for message in requester.processed] == ["memo1"]
    assert secretary.delivered_memos == []


def test_a_hook_waiting_on_io_does_not_hold_up_a_requested_stop(secretary: Secretary):
    """The loop awaits this hook directly, so one waiting on I/O holds shutdown for as long as it takes.

    A caller working to a deadline it does not control would never reach `finalize`, which is where the
    run reports and cleans up.
    """

    class Bus(MockOrchestrator):
        async def on_message_received(self, message: BaseMessage):
            await super().on_message_received(message)
            await asyncio.sleep(30)

    orchestrator = Bus(logging.getLogger("test_hook_stop"), max_timeout=60, grace_period=1)
    orchestrator.register_processor(secretary, [Memo])
    orchestrator.submit_message(Memo("memo1"))
    threading.Timer(0.3, orchestrator.request_shutdown, args=(ShutdownRequest.cancelled(),)).start()

    start = time.perf_counter()
    orchestrator.run()
    elapsed = time.perf_counter() - start

    assert elapsed < 5
    assert "finalize" in orchestrator.events
    # Abandoned before dispatch, so the message it was about never reaches a processor.
    assert secretary.delivered_memos == []


class ScopedProcessor(AsyncProcessor[Memo]):
    def __init__(self, name: str, monitor: ComponentMonitor):
        super().__init__(name)
        self.monitor = monitor

    async def process_message(self, message: Memo):
        self.monitor.metrics.count("attempted", tags={"tag": message.id})
        if message.content.startswith("fail_processing"):
            raise ValueError("Processing failed intentionally")

    async def on_success(self, message: Memo):
        self.monitor.metrics.count("confirmed", tags={"tag": message.id})

    async def on_error(self, error: MessageProcessingError | ProcessorHookError):
        self.monitor.metrics.count("handled", tags={"tag": error.message.id})


def make_memo_scope(runtime: MonitoringRuntime) -> Callable[[BaseMessage], AbstractContextManager[None]]:
    context = runtime.context

    def scope(message: BaseMessage) -> AbstractContextManager[None]:
        return context.scope({"memo_id": message.id})

    return scope


def test_a_message_scope_covers_processing_and_the_success_and_error_hooks():
    sink = RecordingSink()
    runtime = MonitoringRuntime(metrics_sink=sink)
    orchestrator = MockOrchestrator(
        logging.getLogger("test_scope"), grace_period=0.1, message_scope=make_memo_scope(runtime)
    )
    orchestrator.register_processor(ScopedProcessor("scoped", runtime.component("scoped")), [Memo])
    orchestrator.submit_message(Memo("failing_memo", content="fail_processing"))
    orchestrator.submit_message(Memo("ok_memo"))
    orchestrator.run()

    assert [record.name for record in sink.records] == ["attempted", "handled", "attempted", "confirmed"]
    for record in sink.records:
        assert record.fields["memo_id"] == record.tags["tag"]
    assert runtime.context.fields == {}


def test_concurrent_sync_processors_keep_their_message_scopes_apart():
    sink = RecordingSink()
    runtime = MonitoringRuntime(metrics_sink=sink)
    overlap = threading.Barrier(2, timeout=5)

    class OverlappingWorker(SyncProcessor[Memo]):
        def __init__(self, name: str, monitor: ComponentMonitor):
            super().__init__(name)
            self.monitor = monitor

        def process_message(self, message: Memo):
            overlap.wait()
            self.monitor.metrics.count("worked", tags={"tag": message.id})

    with ThreadPoolExecutor(max_workers=2) as lent:
        orchestrator = MockOrchestrator(
            logging.getLogger("test_scoped_sync"),
            grace_period=0.1,
            executor=lent,
            message_scope=make_memo_scope(runtime),
        )
        orchestrator.register_processor(OverlappingWorker("worker", runtime.component("worker")), [Memo])
        orchestrator.submit_message(Memo("memo1"))
        orchestrator.submit_message(Memo("memo2"))
        orchestrator.run()

    observed = {(record.fields["memo_id"], record.tags["tag"]) for record in sink.records}
    assert observed == {("memo1", "memo1"), ("memo2", "memo2")}
    assert len(sink.records) == 2


@pytest.mark.parametrize("holding_hook", ["on_initialize", "on_message_received"], ids=["initialize", "message_loop"])
@pytest.mark.asyncio
async def test_a_cancelled_bus_drains_the_hook_it_awaits_before_finalizing(holding_hook: str):
    """Cancellation must release the hook's resources before finalization uses them."""
    lock = asyncio.Lock()
    hook_started = asyncio.Event()
    release_hook = asyncio.Event()
    lifecycle: list[tuple[str, bool]] = []

    class Bus(MockOrchestrator):
        async def _hold_resource(self) -> None:
            async with lock:
                hook_started.set()
                try:
                    await release_hook.wait()
                finally:
                    lifecycle.append(("hook released", self.stopping))

        async def on_initialize(self) -> None:
            if holding_hook == "on_initialize":
                await self._hold_resource()

        async def on_message_received(self, message: BaseMessage) -> None:
            if holding_hook == "on_message_received":
                await self._hold_resource()

        async def on_finalize(self, exception: Exception | None) -> None:
            lifecycle.append(("finalize", self.stopping))
            async with lock:
                await super().on_finalize(exception)

    bus = Bus(logging.getLogger("test_cancel_drains_hook"), max_timeout=10, grace_period=1)
    if holding_hook == "on_message_received":
        bus.register_processor(Secretary("memo-taker"), [Memo])
        bus.submit_message(Memo("hold-the-lock"))

    run = asyncio.create_task(bus._entry_point())
    try:
        await asyncio.wait_for(hook_started.wait(), timeout=2)
        run.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(run, timeout=2)
        assert lifecycle == [("hook released", True), ("finalize", True)]
    finally:
        release_hook.set()
        if not run.done():
            run.cancel()
        await asyncio.gather(run, return_exceptions=True)


@pytest.mark.parametrize("hook_name", [HookName.ON_INITIALIZE, HookName.ON_MESSAGE_RECEIVED, HookName.ON_FINALIZE])
@pytest.mark.parametrize("fail_fast", [False, True])
@pytest.mark.asyncio
async def test_shutdown_interrupts_pending_error_recovery(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, hook_name: HookName, fail_fast: bool
):
    """Shutdown must drain pending recovery and apply the error policy to its original failure."""
    monkeypatch.setattr("ddev.event_bus.orchestrator.STOP_CHECK_INTERVAL", 0.005)
    handler_started = asyncio.Event()
    handler_finished = asyncio.Event()
    release_handler = asyncio.Event()
    original_error = ValueError("hook failed")
    errors: list[OrchestratorHookError] = []

    class Bus(MockOrchestrator):
        async def on_initialize(self) -> None:
            if hook_name is HookName.ON_INITIALIZE:
                raise original_error

        async def on_message_received(self, message: BaseMessage) -> None:
            if hook_name is HookName.ON_MESSAGE_RECEIVED:
                raise original_error

        async def on_finalize(self, exception: Exception | None) -> None:
            await super().on_finalize(exception)
            if hook_name is HookName.ON_FINALIZE:
                raise original_error

        async def on_error(self, error: OrchestratorHookError) -> None:
            errors.append(error)
            handler_started.set()
            try:
                await release_handler.wait()
            finally:
                handler_finished.set()

    bus = Bus(logging.getLogger("test_shutdown_error_recovery"), grace_period=0.01, fail_fast=fail_fast)
    if hook_name is HookName.ON_MESSAGE_RECEIVED:
        bus.register_processor(Secretary("memo-taker"), [Memo])
        bus.submit_message(Memo("failed-hook"))

    run = asyncio.create_task(bus._entry_point())
    try:
        await asyncio.wait_for(handler_started.wait(), timeout=2)
        bus.request_shutdown(ShutdownRequest.cancelled())
        if fail_fast:
            with pytest.raises(OrchestratorHookError) as exc_info:
                await asyncio.wait_for(run, timeout=2)
            assert exc_info.value is errors[0]
        else:
            await asyncio.wait_for(run, timeout=2)
            assert "unhandled error:" in caplog.text
        assert errors[0].original_exception is original_error
        assert handler_finished.is_set()
        assert "finalize" in bus.events
    finally:
        release_handler.set()
        if not run.done():
            run.cancel()
        await asyncio.gather(run, return_exceptions=True)


def test_an_async_recovery_handler_still_runs_during_ordinary_finalization():
    """Normal finalization must allow asynchronous error recovery to finish."""
    recovered: list[OrchestratorHookError] = []

    class Bus(MockOrchestrator):
        async def on_finalize(self, exception: Exception | None):
            raise RuntimeError("finalize failed")

        async def on_error(self, error: OrchestratorHookError):
            await asyncio.sleep(0.05)
            recovered.append(error)

    bus = Bus(logging.getLogger("test_finalize_recovery"), grace_period=0.1)
    bus.run()

    assert [error.hook_name for error in recovered] == [HookName.ON_FINALIZE]
    assert bus.shutdown_request is None
