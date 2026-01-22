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

from ddev.event_bus.exceptions import TaskQueueError
from ddev.event_bus.orchestrator import AsyncTask, BaseMessage, EventBusOrchestrator, SyncTask

# Test Structure Documentation
# --------------------------
#
# This test module uses a semantic structure to simulate a realistic event bus scenario.
#
# Messages:
# - EmailMessage: Represents an email to be sent. Contains a 'subject' and 'body'.
# - GenerateReport: Represents a request to generate a report. Contains a 'report_type' and 'priority'.
# - SystemEvent: Represents a system-level event. Contains an 'event_type' and 'urgent' flag.
#
# Tasks:
# - MailServer:
#   - Subscribes to: EmailMessage
#   - Action: Simulates sending an email. Tracks sent emails, delivery confirmations, and failures.
#   - Hooks: Implements custom on_success and on_error hooks for testing hook failures.
#
# - ReportWorker:
#   - Subscribes to: GenerateReport, SystemEvent
#   - Action: Simulates generating a report or handling a system event. Tracks generated reports.
#   - Error Handling: Uses default on_success and on_error hooks (unless overridden in specific tests).
#
# - WorkflowManager:
#   - Subscribes to: EmailMessage (in specific test cases)
#   - Action: Demonstrates task chaining. When it receives a specific EmailMessage, it submits a new
#             GenerateReport and SystemEvent messages.
#
# Diagram:
#
# [Orchestrator]
#      |
#      +---(EmailMessage)----> [MailServer]
#      |                          |
#      |                          +--> (Success/Error Hooks)
#      |
#      +---(GenerateReport, SystemEvent)--> [ReportWorker]
#      |
#      +---(EmailMessage)----> [WorkflowManager] --(GenerateReport, SystemEvent)--> [ReportWorker]


@dataclass
class EmailMessage(BaseMessage):
    subject: str = ""
    body: str = "default"


@dataclass
class GenerateReport(BaseMessage):
    report_type: str = ""
    priority: int = 0


@dataclass
class SystemEvent(BaseMessage):
    event_type: str = ""
    urgent: bool = False


class MailServer(AsyncTask[EmailMessage]):
    def __init__(self, name: str):
        super().__init__(name)
        self.sent_emails: list[BaseMessage] = []
        self.delivery_confirmations: list[BaseMessage] = []
        self.failed_deliveries: list[tuple[BaseMessage, Exception]] = []

    async def process_message(self, message: EmailMessage) -> None:
        if isinstance(message, EmailMessage) and message.body.startswith("fail_processing"):
            raise ValueError("Processing failed intentionally")
        self.sent_emails.append(message)

    async def on_success(self, message: EmailMessage) -> None:
        if isinstance(message, EmailMessage) and message.body == "fail_success_hook":
            raise RuntimeError("Success hook failed intentionally")
        self.delivery_confirmations.append(message)

    async def on_error(self, message: EmailMessage, error: Exception) -> None:
        if isinstance(message, EmailMessage) and message.body == "fail_processing_and_error":
            raise RuntimeError("Error hook failed intentionally")
        self.failed_deliveries.append((message, error))


class ReportWorker(AsyncTask[GenerateReport | SystemEvent]):
    def __init__(self, name: str):
        super().__init__(name)
        self.generated_reports: list[BaseMessage] = []

    async def process_message(self, message: GenerateReport | SystemEvent) -> None:
        if isinstance(message, GenerateReport) and message.priority < 0:
            raise ValueError("ReportWorker failed intentionally")
        self.generated_reports.append(message)


class WorkflowManager(AsyncTask[EmailMessage]):
    def __init__(self, name: str):
        super().__init__(name)
        self.processed_messages: list[EmailMessage] = []

    async def process_message(self, message: EmailMessage) -> None:
        self.processed_messages.append(message)
        if isinstance(message, EmailMessage):
            if message.subject == "register_user":
                self.submit_message(SystemEvent(id="register_user", urgent=False, event_type="RegisterUserEmail"))
            else:
                self.submit_message(GenerateReport(id="chained_report", priority=100, report_type="ChainedReport"))


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
def mail_server() -> MailServer:
    return MailServer("mail_server")


@pytest.fixture
def report_worker() -> ReportWorker:
    return ReportWorker("report_worker")


@pytest.fixture
def workflow_manager() -> WorkflowManager:
    return WorkflowManager("workflow_manager")


@pytest.fixture
def orchestrator(
    mail_server: MailServer, report_worker: ReportWorker, workflow_manager: WorkflowManager
) -> MockOrchestrator:
    logger = logging.getLogger("test_orchestrator")
    # Use a short grace_period for tests to speed them up (0.1s instead of default 10s)
    orchestrator = MockOrchestrator(logger, grace_period=0.1)

    orchestrator.register_task(mail_server, [EmailMessage])
    orchestrator.register_task(report_worker, [GenerateReport, SystemEvent])
    orchestrator.register_task(workflow_manager, [EmailMessage])

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
    mail_server: MailServer,
    report_worker: ReportWorker,
    workflow_manager: WorkflowManager,
) -> None:
    welcome_email = EmailMessage("welcome_email", subject="register_user", body="hello")

    orchestrator.submit(welcome_email)
    orchestrator.run()

    # Check Orchestrator State
    assert "initialize" in orchestrator.events
    assert "finalize" in orchestrator.events

    # Check MailServer State
    assert len(mail_server.sent_emails) == 1
    assert welcome_email in mail_server.sent_emails
    assert len(mail_server.delivery_confirmations) == 1
    assert len(mail_server.failed_deliveries) == 0

    # Check ReportWorker State
    # Received one system event to register the new user
    assert len(report_worker.generated_reports) == 1
    assert isinstance(report_worker.generated_reports[0], SystemEvent)
    assert report_worker.generated_reports[0].id == "register_user"

    # Check WorkflowManager State
    assert len(workflow_manager.processed_messages) == 1


@pytest.mark.parametrize(
    "msg_body, expected_error_type",
    [
        ("fail_processing", ValueError),
    ],
)
def test_task_processing_failure(
    orchestrator: MockOrchestrator,
    mail_server: MailServer,
    msg_body: str,
    expected_error_type: type[Exception],
) -> None:
    orchestrator.submit(EmailMessage("failed_email", body=msg_body))

    orchestrator.run()

    # MailServer should have failed processing
    assert len(mail_server.sent_emails) == 0
    assert len(mail_server.delivery_confirmations) == 0
    assert len(mail_server.failed_deliveries) == 1

    failed_msg, error = mail_server.failed_deliveries[0]
    assert failed_msg.id == "failed_email"
    assert isinstance(error, expected_error_type)


def test_task_success_hook_failure(orchestrator: MockOrchestrator, mail_server: MailServer) -> None:
    orchestrator.submit(EmailMessage("hook_fail_email", body="fail_success_hook"))
    orchestrator.run()

    # Processing succeeded
    assert len(mail_server.sent_emails) == 1
    # But success hook failed
    assert len(mail_server.delivery_confirmations) == 0

    # Error hook should NOT be called for success hook failure
    assert len(mail_server.failed_deliveries) == 0


def test_mixed_messages(orchestrator: MockOrchestrator, mail_server: MailServer, report_worker: ReportWorker) -> None:
    orchestrator.submit(EmailMessage("email1"))
    orchestrator.submit(GenerateReport("report1"))
    orchestrator.submit(SystemEvent("event1"))
    orchestrator.submit(EmailMessage("email2"))

    orchestrator.run()

    assert len(mail_server.sent_emails) == 2
    # 2 explicit reports + 2 chained reports from WorkflowManager (triggered by the 2 emails)
    assert len(report_worker.generated_reports) == 4


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


def test_default_on_error(
    orchestrator: MockOrchestrator, report_worker: ReportWorker, caplog: pytest.LogCaptureFixture
) -> None:
    # ReportWorker uses default on_error (pass)
    orchestrator.submit(GenerateReport("bad_report", priority=-1))
    orchestrator.run()

    assert len(report_worker.generated_reports) == 0
    assert "finalize" in orchestrator.events
    assert "ReportWorker failed intentionally" in caplog.text


def test_task_on_error_failure(
    orchestrator: MockOrchestrator,
    mail_server: MailServer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestrator.submit(EmailMessage("double_fail_email", body="fail_processing_and_error"))

    orchestrator.run()

    assert len(mail_server.sent_emails) == 0
    assert len(mail_server.failed_deliveries) == 0

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
            return EmailMessage("recovered")
        return await original_get()

    mocker.patch.object(orchestrator._queue, "get", side_effect=side_effect)

    orchestrator.run()

    # Should have received the recovered message
    assert any(m.id == "recovered" for m in orchestrator.received_messages)


def test_max_timeout_interruption(orchestrator: MockOrchestrator) -> None:
    # Set a very short max_timeout
    orchestrator._max_timeout = 0.5
    orchestrator._grace_period = 5.0  # Long grace period

    class LongTask(AsyncTask[EmailMessage]):
        async def process_message(self, message: EmailMessage):
            await asyncio.sleep(2.0)

    task_long = LongTask("long")
    orchestrator.register_task(task_long, [EmailMessage])

    orchestrator.submit(EmailMessage("slow_email"))

    with assert_time(0.5, 1.5):
        orchestrator.run()


def test_sync_task_thread_execution(orchestrator: MockOrchestrator, mail_server: MailServer) -> None:
    import threading

    class CPUBoundTask(SyncTask[SystemEvent]):
        def __init__(self, name: str):
            super().__init__(name)
            self.executed = False
            self.thread_id: int | None = None

        def process_message(self, message: SystemEvent):
            self.executed = True
            self.thread_id = threading.get_ident()
            time.sleep(0.1)  # Simulate work

    cpu_task = CPUBoundTask("cpu_bound")
    orchestrator.register_task(cpu_task, [SystemEvent])

    orchestrator.submit(SystemEvent("cpu_event"))
    orchestrator.submit(EmailMessage("async_email"))
    orchestrator.run()

    assert cpu_task.executed
    assert cpu_task.thread_id is not None

    # Validate it actually run in a different thread than the main loop
    # All async tasks are run in the main thread.
    assert cpu_task.thread_id != threading.get_ident()

    # Verify async task also ran
    assert len(mail_server.sent_emails) == 1
    assert mail_server.sent_emails[0].id == "async_email"


def test_task_submit_without_bus() -> None:
    task = MailServer("orphan")
    with pytest.raises(TaskQueueError, match="This task has not been added"):
        task.submit_message(EmailMessage("fail"))
