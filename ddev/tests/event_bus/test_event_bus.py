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

from ddev.event_bus.exceptions import ProcessorQueueError
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

    async def process_message(self, message: Memo) -> None:
        if message.content.startswith("fail_processing"):
            raise ValueError("Processing failed intentionally")
        self.delivered_memos.append(message)

    async def on_success(self, message: Memo) -> None:
        if message.content == "fail_success_hook":
            raise RuntimeError("Success hook failed intentionally")
        self.confirmations.append(message)

    async def on_error(self, message: Memo, error: Exception) -> None:
        if message.content == "fail_processing_and_error":
            raise RuntimeError("Error hook failed intentionally")
        self.failed_deliveries.append((message, error))


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
    def __init__(self, logger: logging.Logger, max_timeout: float = 300, grace_period: float = 10):
        super().__init__(logger=logger, max_timeout=max_timeout, grace_period=grace_period)
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
    orchestrator.submit_message(Memo("failed_memo", content=memo_content))

    orchestrator.run()

    # Secretary should have failed processing
    assert len(secretary.delivered_memos) == 0
    assert len(secretary.confirmations) == 0
    assert len(secretary.failed_deliveries) == 1

    failed_msg, error = secretary.failed_deliveries[0]
    assert failed_msg.id == "failed_memo"
    assert isinstance(error, expected_error_type)


def test_processor_success_hook_failure(orchestrator: MockOrchestrator, secretary: Secretary) -> None:
    orchestrator.submit_message(Memo("hook_fail_memo", content="fail_success_hook"))
    orchestrator.run()

    # Processing succeeded
    assert len(secretary.delivered_memos) == 1
    # But success hook failed
    assert len(secretary.confirmations) == 0

    # Error hook should NOT be called for success hook failure
    assert len(secretary.failed_deliveries) == 0


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


def test_default_on_error(orchestrator: MockOrchestrator, analyst: Analyst, caplog: pytest.LogCaptureFixture) -> None:
    # Analyst uses default on_error (pass)
    orchestrator.submit_message(TaskAssignment("bad_task", priority=-1))
    orchestrator.run()

    assert len(analyst.completed_tasks) == 0
    assert "finalize" in orchestrator.events
    assert "Analyst failed intentionally" in caplog.text


def test_processor_on_error_failure(
    orchestrator: MockOrchestrator,
    secretary: Secretary,
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestrator.submit_message(Memo("double_fail_memo", content="fail_processing_and_error"))

    orchestrator.run()

    assert len(secretary.delivered_memos) == 0
    assert len(secretary.failed_deliveries) == 0

    # The orchestrator should have caught the double failure and continued
    assert "finalize" in orchestrator.events
    # We should have logged the error
    assert "Error hook failed intentionally" in caplog.text


def test_no_subscribers() -> None:
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    # Should exit immediately
    with assert_time(0.0, 0.5):
        orchestrator.run()

    assert "initialize" in orchestrator.events
    assert "finalize" in orchestrator.events
    assert len(orchestrator.received_messages) == 0


def test_initialization_failure() -> None:
    logger = logging.getLogger("test")
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    async def on_init_fail():
        raise RuntimeError("Init failed")

    orchestrator.on_initialize = on_init_fail

    with pytest.raises(RuntimeError, match="Init failed"):
        orchestrator.run()

    # Finalize should still be called
    assert "finalize" in orchestrator.events


def test_queue_retrieval_error(orchestrator: MockOrchestrator, mocker: MockerFixture) -> None:
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
        async def process_message(self, message: Memo):
            await asyncio.sleep(2.0)

    slow_processor = SlowProcessor("slow_processor")
    orchestrator.register_processor(slow_processor, [Memo])

    orchestrator.submit_message(Memo("slow_memo"))

    with assert_time(0.5, 1.5):
        orchestrator.run()


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
