# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager
from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass

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
)
from ddev.event_bus.orchestrator import AsyncProcessor, BaseMessage, EventBusOrchestrator, SyncProcessor

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

    async def process_message(self, message: Memo) -> None:
        if message.content.startswith("fail_processing"):
            raise ValueError("Processing failed intentionally")
        self.delivered_memos.append(message)

    async def on_success(self, message: Memo) -> None:
        if message.content == "fail_success_hook":
            raise RuntimeError("Success hook failed intentionally")
        self.confirmations.append(message)

    async def on_error(self, error: Exception) -> None:
        if isinstance(error, MessageProcessingError):
            if error.message.content == "fail_processing_and_error":
                raise RuntimeError("Error hook failed intentionally")
            self.failed_deliveries.append((error.message, error.original_exception))
        elif isinstance(error, ProcessorHookError):
            self.hook_failures.append(error)


class Analyst(AsyncProcessor[TaskAssignment | Announcement]):
    def __init__(self, name: str):
        super().__init__(name)
        self.completed_tasks: list[BaseMessage] = []

    async def process_message(self, message: TaskAssignment | Announcement) -> None:
        if isinstance(message, TaskAssignment) and message.priority < 0:
            raise ValueError("Analyst failed intentionally")
        self.completed_tasks.append(message)


class Manager(AsyncProcessor[Memo]):
    def __init__(self, name: str):
        super().__init__(name)
        self.processed_memos: list[Memo] = []

    async def process_message(self, message: Memo) -> None:
        self.processed_memos.append(message)
        if message.subject == "new_hire":
            self.submit_message(Announcement(id="new_hire", urgent=False, announcement_type="NewHireAnnouncement"))
        else:
            self.submit_message(TaskAssignment(id="delegated_task", priority=100, task_type="DelegatedTask"))


class MockOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        logger: logging.Logger,
        max_timeout: float = 300,
        grace_period: float = 10,
        fail_fast: bool = False,
    ):
        super().__init__(
            logger=logger,
            max_timeout=max_timeout,
            grace_period=grace_period,
            fail_fast=fail_fast,
        )
        self.events: list[str] = []
        self.received_messages: list[BaseMessage] = []
        self.finalized_exception: Exception | None = None

    async def on_initialize(self) -> None:
        self.events.append("initialize")

    async def on_finalize(self, exception: Exception | None) -> None:
        self.events.append("finalize")
        self.finalized_exception = exception

    async def on_message_received(self, message: BaseMessage) -> None:
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
) -> None:
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
) -> None:
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


def test_processor_success_hook_failure_routed_to_on_error(
    orchestrator: MockOrchestrator, secretary: Secretary
) -> None:
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


def test_mixed_messages(orchestrator: MockOrchestrator, secretary: Secretary, analyst: Analyst) -> None:
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
) -> None:
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
def test_validate_parameters(max_timeout: float, grace_period: float, expectation: AbstractContextManager) -> None:
    logger = logging.getLogger("test")
    with expectation:
        MockOrchestrator(logger, max_timeout=max_timeout, grace_period=grace_period)


def test_default_on_error_with_default_policy_logs_and_continues(
    orchestrator: MockOrchestrator, analyst: Analyst, caplog: pytest.LogCaptureFixture
) -> None:
    """Analyst uses the default re-raising on_error; under fail_fast=False the bus logs and continues."""
    orchestrator.submit_message(TaskAssignment("bad_task", priority=-1))
    orchestrator.run()

    assert len(analyst.completed_tasks) == 0
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None
    assert "Analyst failed intentionally" in caplog.text


def test_default_on_error_with_fail_fast_stops_bus(secretary: Secretary, analyst: Analyst, manager: Manager) -> None:
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
) -> None:
    """on_error itself raising a non-Fatal error is logged under fail_fast=False; bus continues."""
    orchestrator.submit_message(Memo("double_fail_memo", content="fail_processing_and_error"))

    orchestrator.run()

    assert len(secretary.delivered_memos) == 0
    assert len(secretary.failed_deliveries) == 0
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None
    assert "Error hook failed intentionally" in caplog.text


def test_processor_on_error_failure_stops_bus_under_fail_fast(secretary: Secretary) -> None:
    """on_error itself raising a non-Fatal error stops the bus when fail_fast=True."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)
    orchestrator.register_processor(secretary, [Memo])

    orchestrator.submit_message(Memo("double_fail_memo", content="fail_processing_and_error"))

    with pytest.raises(RuntimeError, match="Error hook failed intentionally"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert isinstance(orchestrator.finalized_exception, RuntimeError)


def test_on_error_returning_cleanly_continues_under_fail_fast(secretary: Secretary) -> None:
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


def test_processor_on_error_recovers_processing_failure(orchestrator: MockOrchestrator, secretary: Secretary) -> None:
    """process_message() failures handled by on_error keep the bus running normally."""
    orchestrator.submit_message(Memo("recoverable_memo", content="fail_processing"))
    orchestrator.submit_message(Memo("ok_memo", content="ok"))

    orchestrator.run()

    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None
    assert len(secretary.delivered_memos) == 1
    assert secretary.delivered_memos[0].id == "ok_memo"
    assert len(secretary.failed_deliveries) == 1


def test_no_subscribers() -> None:
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    # Should exit immediately
    with assert_time(0.0, 0.5):
        orchestrator.run()

    assert "initialize" in orchestrator.events
    assert "finalize" in orchestrator.events
    assert len(orchestrator.received_messages) == 0


def test_initialization_failure_under_fail_fast() -> None:
    """on_initialize failures route through orchestrator on_error; fail_fast surfaces them."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)

    async def on_init_fail():
        raise RuntimeError("Init failed")

    orchestrator.on_initialize = on_init_fail

    with pytest.raises(OrchestratorHookError) as exc_info:
        orchestrator.run()

    assert exc_info.value.hook_name is HookName.ON_INITIALIZE
    assert isinstance(exc_info.value.original_exception, RuntimeError)
    assert str(exc_info.value.original_exception) == "Init failed"
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is exc_info.value


def test_initialization_failure_swallowed_under_default_policy(caplog: pytest.LogCaptureFixture) -> None:
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


def test_orchestrator_on_error_can_handle_initialization_failure() -> None:
    """A custom orchestrator on_error can swallow init failures cleanly."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)

    seen: list[OrchestratorHookError] = []

    async def on_init_fail():
        raise RuntimeError("Init failed")

    async def on_error_handle(error):
        seen.append(error)
        # Return cleanly = handled

    orchestrator.on_initialize = on_init_fail  # type: ignore[method-assign]
    orchestrator.on_error = on_error_handle  # type: ignore[method-assign]

    orchestrator.run()

    assert len(seen) == 1
    assert seen[0].hook_name is HookName.ON_INITIALIZE
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is None


def test_finalize_receives_exception_on_process_messages_failure(mocker: MockerFixture) -> None:
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


def test_queue_retrieval_error(orchestrator: MockOrchestrator, mocker: MockerFixture) -> None:
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


def test_max_timeout_interruption(orchestrator: MockOrchestrator) -> None:
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


def test_sync_processor_thread_execution(orchestrator: MockOrchestrator, secretary: Secretary) -> None:
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


def test_processor_submit_without_bus() -> None:
    processor = Secretary("orphan")
    with pytest.raises(ProcessorQueueError, match="This processor has not been added"):
        processor.submit_message(Memo("fail"))


def test_fatal_processing_error_stops_orchestrator(orchestrator: MockOrchestrator) -> None:
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


def test_orchestrator_hook_failure_stops_bus_under_fail_fast(secretary: Secretary) -> None:
    """on_message_received failure routes through orchestrator on_error; fail_fast surfaces it."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)
    orchestrator.register_processor(secretary, [Memo])

    async def on_message_boom(message: BaseMessage):
        raise RuntimeError("orchestrator hook boom")

    orchestrator.on_message_received = on_message_boom  # type: ignore[method-assign]

    orchestrator.submit_message(Memo("boom_msg"))
    orchestrator.submit_message(Memo("never_dispatched"))

    with pytest.raises(OrchestratorHookError) as exc_info:
        orchestrator.run()

    assert exc_info.value.hook_name is HookName.ON_MESSAGE_RECEIVED
    assert isinstance(exc_info.value.original_exception, RuntimeError)
    assert "finalize" in orchestrator.events
    assert orchestrator.finalized_exception is exc_info.value
    assert len(secretary.delivered_memos) == 0


def test_orchestrator_hook_failure_swallowed_under_default_policy(
    secretary: Secretary, caplog: pytest.LogCaptureFixture
) -> None:
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


def test_processor_on_error_can_signal_fatal(orchestrator: MockOrchestrator, secretary: Secretary) -> None:
    """on_error raising FatalProcessingError stops the bus regardless of fail_fast."""

    async def fatal_on_error(error: Exception) -> None:
        raise FatalProcessingError("on_error decided to stop the bus")

    secretary.on_error = fatal_on_error  # type: ignore[method-assign]

    orchestrator.submit_message(Memo("trigger_fatal", content="fail_processing"))

    with pytest.raises(FatalProcessingError, match="on_error decided to stop the bus"):
        orchestrator.run()

    assert "finalize" in orchestrator.events
    assert isinstance(orchestrator.finalized_exception, FatalProcessingError)
    assert len(secretary.delivered_memos) == 0


def test_finalize_failure_swallowed_under_default_policy(caplog: pytest.LogCaptureFixture) -> None:
    """Under fail_fast=False on_finalize failures route through on_error and are absorbed."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    async def on_finalize_boom(exception: Exception | None) -> None:
        orchestrator.events.append("finalize")
        raise RuntimeError("finalize boom")

    orchestrator.on_finalize = on_finalize_boom  # type: ignore[method-assign]

    orchestrator.run()

    assert "finalize" in orchestrator.events
    assert "finalize boom" in caplog.text


def test_finalize_failure_propagates_under_fail_fast() -> None:
    """Under fail_fast=True on_finalize failures escape from run()."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)

    async def on_finalize_boom(exception: Exception | None) -> None:
        orchestrator.events.append("finalize")
        raise RuntimeError("finalize boom")

    orchestrator.on_finalize = on_finalize_boom  # type: ignore[method-assign]

    with pytest.raises(OrchestratorHookError) as exc_info:
        orchestrator.run()

    assert exc_info.value.hook_name is HookName.ON_FINALIZE
    assert isinstance(exc_info.value.original_exception, RuntimeError)
    assert "finalize" in orchestrator.events


def test_finalize_failure_takes_precedence_over_earlier_exception_under_fail_fast() -> None:
    """When init and finalize both fail under fail_fast=True, the finalize failure surfaces."""
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1, fail_fast=True)

    saw_exception: list[Exception | None] = []

    async def on_init_fail() -> None:
        raise RuntimeError("init failed")

    async def on_finalize_boom(exception: Exception | None) -> None:
        orchestrator.events.append("finalize")
        saw_exception.append(exception)
        raise RuntimeError("finalize boom")

    orchestrator.on_initialize = on_init_fail  # type: ignore[method-assign]
    orchestrator.on_finalize = on_finalize_boom  # type: ignore[method-assign]

    with pytest.raises(OrchestratorHookError) as exc_info:
        orchestrator.run()

    assert exc_info.value.hook_name is HookName.ON_FINALIZE
    assert isinstance(exc_info.value.original_exception, RuntimeError)
    assert str(exc_info.value.original_exception) == "finalize boom"

    # on_finalize received the wrapped initialization failure
    assert len(saw_exception) == 1
    init_err = saw_exception[0]
    assert isinstance(init_err, OrchestratorHookError)
    assert init_err.hook_name is HookName.ON_INITIALIZE


def test_should_process_message_conditional_filtering(bare_orchestrator: MockOrchestrator) -> None:
    """Processor processes only messages matching a custom predicate on message attributes."""

    class HighPriorityAnalyst(AsyncProcessor[TaskAssignment]):
        def __init__(self, name: str, min_priority: int):
            super().__init__(name)
            self.min_priority = min_priority
            self.processed: list[TaskAssignment] = []

        def should_process_message(self, message: BaseMessage) -> bool:
            return isinstance(message, TaskAssignment) and message.priority >= self.min_priority

        async def process_message(self, message: TaskAssignment) -> None:
            self.processed.append(message)

    analyst = HighPriorityAnalyst("high_priority_analyst", min_priority=10)
    bare_orchestrator.register_processor(analyst, [TaskAssignment])

    bare_orchestrator.submit_message(TaskAssignment("low_task", priority=1))
    bare_orchestrator.submit_message(TaskAssignment("high_task", priority=100))
    bare_orchestrator.run()

    assert len(analyst.processed) == 1
    assert analyst.processed[0].id == "high_task"


def test_should_process_message_is_independent_per_processor(
    bare_orchestrator: MockOrchestrator, secretary: Secretary
) -> None:
    """Each processor filters independently — one skipping a message does not affect the others."""

    class UrgentMemosOnlyProcessor(AsyncProcessor[Memo]):
        def __init__(self, name: str):
            super().__init__(name)
            self.processed: list[Memo] = []

        def should_process_message(self, message: BaseMessage) -> bool:
            return isinstance(message, Memo) and message.subject == "urgent"

        async def process_message(self, message: Memo) -> None:
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
