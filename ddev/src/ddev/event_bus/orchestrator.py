# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import contextlib
import logging
from abc import ABC, abstractmethod
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import assert_never

from .exceptions import FatalProcessingError, MessageProcessingError, ProcessorQueueError, ProcessorSuccessHookError


@dataclass
class BaseMessage:
    """
    Base class for all messages. Messages are dataclasses that hold the data to be sent.

    All messages must include an id to identify the particular message instance.
    """

    id: str


class BaseProcessor[T: BaseMessage]:
    def __init__(self, name: str):
        self.name = name
        self.queue: asyncio.Queue[BaseMessage] | None = None

    async def on_success(self, message: T) -> None:
        pass

    async def on_error(self, message: T, error: Exception) -> None:
        pass

    def submit_message(self, message: BaseMessage) -> None:
        if self.queue is None:
            raise ProcessorQueueError("This processor has not been added to an active event bus")
        self.queue.put_nowait(message)


class AsyncProcessor[T: BaseMessage](BaseProcessor[T], ABC):
    @abstractmethod
    async def process_message(self, message: T) -> None: ...


class SyncProcessor[T: BaseMessage](BaseProcessor[T], ABC):
    @abstractmethod
    def process_message(self, message: T) -> None: ...


type Processor[T: BaseMessage] = AsyncProcessor[T] | SyncProcessor[T]


class EventBusOrchestrator(ABC):
    """
    EventBus engine that handles the message polling and processor execution.
    """

    def __init__(
        self,
        logger: logging.Logger,
        max_timeout: float = 300,
        grace_period: float = 10,
        executor: Executor | None = None,
    ):
        """
        Args:
            logger: The logger to use for the orchestrator.
            max_timeout: The maximum time in seconds to wait for the orchestrator to complete.
            grace_period: The timeout in seconds to wait for a new message to be submitted after all
                messages have been processed.
            executor: The executor to use for running sync processors.
                      The default will be a ThreadpoolExecutor with 4 workers.
        """
        self.__validate_parameters(max_timeout, grace_period)
        self._logger = logger
        self._max_timeout = max_timeout
        self._grace_period = grace_period
        self._executor = executor or ThreadPoolExecutor(max_workers=4)
        self._subscribers: dict[type[BaseMessage], list[Processor]] = {}
        # These will be initialized in the running loop
        self._queue = asyncio.Queue[BaseMessage]()
        self._running = False

    def __validate_parameters(self, max_timeout: float, grace_period: float):
        """
        Validates the parameters passed to the orchestrator.
        """
        if max_timeout <= 0:
            raise ValueError("max_timeout must be greater than 0")
        if grace_period < 0:
            raise ValueError("grace_period must be greater than or equal to 0")
        if max_timeout <= grace_period:
            raise ValueError("max_timeout must be greater than grace_period")

    def register_processor[T: BaseMessage](self, processor: Processor[T], message_types: list[type[T]]):
        """Registers a processor to receive specific message types."""
        processor.queue = self._queue
        for msg_type in message_types:
            self._subscribers.setdefault(msg_type, []).append(processor)

    def submit_message(self, message: BaseMessage):
        """
        Adds a message to the queue.
        """
        self._queue.put_nowait(message)

    def run(self):
        """
        Launch the orchestrator and start consuming messages from the message queue.

        The orchestrator will process messages and submit them to the processors that are subscribed to them.

        The execution flow is as follows:
        - initialize()
          - [hook] on_initialize()
        - process_events()
          - [hook] on_message_received(message)
        - finalize()
          - [hook] on_finalize(exc_info)
        """
        asyncio.run(self._entry_point())

    async def _entry_point(self):
        exception = None
        try:
            await self.initialize()
            await self.process_messages()
        except Exception as e:
            exception = e
            raise
        finally:
            await self.finalize(exception)

    async def initialize(self):
        """
        Initializes the orchestrator.
        """
        self._running = True
        await self.on_initialize()

    @abstractmethod
    async def on_initialize(self):  # pragma: no cover
        """
        Hook for subclasses to perform initial setup (e.g. submit initial messages).
        """
        pass

    async def finalize(self, exception: Exception | None):
        """
        Method called at the end of the execution lifecycle when all processors have been completed.

        In the case that the execution failed, the exception will be passed to the method
        """
        self._running = False
        await self.on_finalize(exception)

    @abstractmethod
    async def on_finalize(self, exception: Exception | None):  # pragma: no cover
        """
        Hook for subclasses to perform final cleanup.
        """
        pass

    @abstractmethod
    async def on_message_received(self, message: BaseMessage):  # pragma: no cover
        """
        Hook for subclasses to perform actions when a message is received.
        """
        pass

    def _remaining_time(self, start_time: float) -> float:
        """
        Calculates the remaining time until the max timeout is reached.
        """
        elapsed = asyncio.get_running_loop().time() - start_time
        return self._max_timeout - elapsed

    async def process_messages(self):
        """
        Continuously reads from the queue and processes the messages by submitting them to the subscribed processors.
        Processing ends when the queue is empty and all processors have been completed.
        """
        # If this is launched without any subscribers, we can exit early
        if not self._subscribers:
            return

        running_tasks = set()
        # Create the initial get task
        get_task = asyncio.create_task(self._queue.get())

        start_time = asyncio.get_running_loop().time()

        try:
            while not await self.__should_stop(start_time, running_tasks, get_task):
                wait_set = running_tasks | {get_task}
                # We use a small timeout to check for max_timeout periodically. If we leave this here blocking
                # we can keep the loop alive much longer than the max_timeout.
                done, _ = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED, timeout=1.0)

                current_get_task = get_task
                if current_get_task in done:
                    get_task = await self.__process_new_message(current_get_task, running_tasks)
                    if get_task is None:
                        break

                self.__process_finished_tasks(done, current_get_task, running_tasks)
        finally:
            # If we exit the loop and tasks are still running (e.g. timeout or forced break),
            # we must clean them up before returning to ensure finalize() runs in a safe state.
            if running_tasks:
                self._logger.info("Cancelling %s remaining tasks...", len(running_tasks))
                for task in running_tasks:
                    task.cancel()

                # Wait for them to actually finish cancelling
                await asyncio.wait(running_tasks)

            # Also ensure the get_task is dead if it's still around
            if get_task and not get_task.done():
                get_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await get_task

    async def __should_stop(self, start_time: float, running_tasks: set[asyncio.Task], get_task: asyncio.Task) -> bool:
        """
        Checks whether the orchestrator should stop. This can happen in two ways:
        - The max timeout is reached
        - The queue is empty and all processors have been completed and the grace period is reached
        """
        # Check first whether we are over the max timeout
        if self._remaining_time(start_time) <= 0:
            self._logger.error(
                "Orchestrator timed out after %s seconds. A total of %s tasks were running.",
                self._max_timeout,
                len(running_tasks),
            )
            get_task.cancel()
            return True

        # Check exit condition: empty queue (implied by get_task not done) and no running processors
        if not running_tasks and not get_task.done() and self._queue.empty():
            try:
                remaining = self._remaining_time(start_time)

                if remaining <= 0:
                    get_task.cancel()
                    return True

                # This ensures we wait for new message for a time period defined by grace_period
                # but capped by max_timeout
                wait_time = min(self._grace_period, remaining)
                await asyncio.wait_for(asyncio.shield(get_task), timeout=wait_time)
            except asyncio.TimeoutError:
                get_task.cancel()
                return True
            except Exception:
                # If the get_task failed, we return False to let the loop handle the exception
                return False

        return False

    async def __process_new_message(
        self,
        get_task: asyncio.Task,
        running_tasks: set[asyncio.Task],
    ) -> asyncio.Task | None:
        """
        Processes a new message from the queue.
        """
        try:
            # Separate the get_task result check to handle its specific errors
            msg = get_task.result()
        except asyncio.CancelledError:
            # get_task was cancelled, stop polling
            return None
        except Exception as e:
            self._logger.error("Error retrieving message from queue: %s", e)

            # Wait briefly to re-submit a get_task again in case there is a transient issue.
            await asyncio.sleep(1.0)

            # Re-create the get_task to keep the loop alive
            return asyncio.create_task(self._queue.get())

        # If we successfully got a message, process it
        try:
            await self.on_message_received(msg)
        except asyncio.CancelledError:
            # If the await suspension raises a CancelledError, we should respect
            # the global shutdown.
            raise
        except FatalProcessingError as e:
            # If the hook raises a FatalProcessingError, we should stop the orchestrator.
            self._logger.error("Fatal error processing on_message_received hook: %s", e)
            return None
        except Exception as e:
            self._logger.warning("Error in on_message_received: %s", e)

        # Launch the processors
        self._handle_message(msg, running_tasks)

        # Always create a new get task if we consumed one
        return asyncio.create_task(self._queue.get())

    def __process_finished_tasks(
        self,
        done: set[asyncio.Task],
        get_task: asyncio.Task,
        running_tasks: set[asyncio.Task],
    ):
        for task in done:
            if task is get_task:
                continue
            running_tasks.discard(task)
            if not task.cancelled() and task.exception():
                self._logger.error("Task failed: %s", task.exception())

    def _handle_message(self, msg: BaseMessage, running_tasks: set[asyncio.Task]):
        """
        Launches asyncio tasks to process the given message by any processors that are subscribed to the message type.

        The `running_tasks` set is updated with the processors that have been launched.
        """
        running_tasks.update(
            asyncio.create_task(self._task_wrapper(processor, msg))
            for processor in self._subscribers.get(type(msg), [])
        )

    async def _task_wrapper(self, processor: Processor, message: BaseMessage):
        """
        Processes a message by the given processor.
        """
        try:
            match processor:
                case AsyncProcessor():
                    await processor.process_message(message)
                case SyncProcessor():
                    await asyncio.get_running_loop().run_in_executor(self._executor, processor.process_message, message)
                case _:
                    assert_never(processor)
        except Exception as e:
            try:
                await processor.on_error(message, e)
            except Exception as hook_error:
                self._logger.error("Error in processor %s on_error: %s", processor.__class__.__name__, hook_error)

            raise MessageProcessingError(processor.name, message, e) from e

        try:
            await processor.on_success(message)
        except Exception as e:
            # Raise a ProcessorSuccessHookError to ensure the error to show that the failure happened even if the
            # process_message call succeeded.
            raise ProcessorSuccessHookError(processor.name, message, e) from e
