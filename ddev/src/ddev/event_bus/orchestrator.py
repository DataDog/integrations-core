# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import contextlib
import contextvars
import logging
import math
import signal
import threading
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from concurrent.futures import wait as wait_for_futures
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from types import FrameType
from typing import assert_never, cast

from .exceptions import (
    FatalProcessingError,
    HookName,
    MessageProcessingError,
    OrchestratorHookError,
    ProcessorHookError,
    ProcessorQueueError,
    SkipMessageError,
)
from .shutdown import ShutdownKind, ShutdownRequest

type ErrorHandler[E: Exception] = Callable[[E], Awaitable[None]]
# What `signal.getsignal` hands back: a Python callable, one of the `SIG_*` constants, or None for a
# handler installed outside Python.
type SignalHandler = Callable[[int, FrameType | None], object] | int | signal.Handlers | None
type MessageScope = Callable[[BaseMessage], AbstractContextManager[None]]

DEFAULT_ORCHESTRATOR_MAX_TIMEOUT = 300.0
# How long the loop may block before re-reading the timeout and the stop flag.
STOP_CHECK_INTERVAL = 1.0
# What a process is asked to stop with: SIGINT from an interactive interrupt, SIGTERM from a scheduler
# or CI runner cancelling the job.
SHUTDOWN_SIGNALS = (signal.SIGINT, signal.SIGTERM)


class OrchestratorTimeout(Exception):
    """Internal signal raised when ``max_timeout`` is exceeded.

    Caught by :meth:`EventBusOrchestrator.process_messages` so the timeout reason can be
    handed to the single cancellation loop in its ``finally`` block, instead of cancelling
    tasks from two places.
    """


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
        # Set by the bus at registration.
        self.bus: EventBusOrchestrator | None = None

    async def on_success(self, message: T) -> None:
        pass

    async def on_error(self, error: MessageProcessingError | ProcessorHookError) -> None:
        """
        Handle a processor-scoped failure.

        Receives a :class:`MessageProcessingError` when ``process_message`` fails, or a
        :class:`ProcessorHookError` when a processor hook (e.g. ``on_success``) fails.
        Both wrappers expose ``.message``, ``.original_exception``, and ``.processor_name``
        so the developer can decide what to do.

        Behavior of the return:
          - Return cleanly: the error is considered handled, processing continues.
          - Raise :class:`FatalProcessingError`: stop the orchestrator.
          - Raise anything else: the orchestrator's ``fail_fast`` policy decides.

        The default implementation re-raises so unmodified processors fall through to
        the orchestrator-level ``fail_fast`` policy.

        Can be cancelled part-way when the bus it belongs to is asked to stop.
        """
        raise error

    def on_stop_requested(self) -> None:
        """React to the bus being asked to wind down, by shortening work already in flight.

        Called once per processor. :attr:`stopping` is already set and the bus may already be acting on
        it, so this cannot assume anything is still running; shorten what is in flight rather than
        expecting to run first. May be called from a signal handler, so it must not block or await.
        Raising is contained: the stop still happens and the other processors are still told.
        """

    def submit_message(self, message: BaseMessage) -> None:
        """Put *message* on the bus this processor was registered in, from any thread."""
        if self.bus is None:
            raise ProcessorQueueError("This processor has not been added to an active event bus")

        self.bus.submit_message(message)

    @property
    def stopping(self) -> bool:
        """Whether the bus is shutting down.

        A `SyncProcessor` runs in a thread, where cancelling its task cannot interrupt it, so long
        work should check this between units and return rather than finish work nobody will read.
        """
        return self.bus is not None and self.bus.stopping

    def should_process_message(self, message: BaseMessage) -> bool:
        return True


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
        max_timeout: float | None = DEFAULT_ORCHESTRATOR_MAX_TIMEOUT,
        grace_period: float = 10,
        executor: Executor | None = None,
        fail_fast: bool = False,
        message_scope: MessageScope | None = None,
    ):
        """
        Args:
            logger: The logger to use for the orchestrator.
            max_timeout: The maximum time in seconds to wait for the orchestrator to complete.
                Defaults to 300 seconds. Pass ``None`` to run with no overall time limit; only
                the idle ``grace_period`` check can stop it.

                Running unbounded removes the only safety net against a hung or
                deadlocked processor and only external cancellation (e.g. Ctrl+C
                or killing the process) will stop it.
            grace_period: The timeout in seconds to wait for a new message to be submitted after all
                messages have been processed.
            executor: The executor to use for running sync processors.
                      The default will be a ThreadpoolExecutor with 4 workers.
            fail_fast: If True, any exception that escapes an ``on_error`` handler stops
                       the orchestrator. If False (default), such exceptions are logged
                       and processing continues. ``FatalProcessingError`` always stops the
                       orchestrator regardless of this flag.
            message_scope: Context manager for each processor invocation, including success/error
                           hooks. Derive context from the message; queues do not transfer it.
        """
        resolved_max_timeout = max_timeout if max_timeout is not None else math.inf
        self.__validate_parameters(resolved_max_timeout, grace_period)
        self._logger = logger
        self._max_timeout = resolved_max_timeout
        self._grace_period = grace_period
        # An executor we were given belongs to the caller, who may reuse it; one we made is ours to
        # shut down, and nobody else can.
        self._owns_executor = executor is None
        self._executor = executor or ThreadPoolExecutor(max_workers=4)
        # Work we put on the pool, so shutdown can wait for it whoever the pool belongs to. Guarded
        # because the pool's own threads discard from it as they finish.
        self._sync_work: set[Future] = set()
        self._sync_work_lock = threading.Lock()
        self._stop_claim = threading.Lock()
        self._message_scope = message_scope
        self._fail_fast = fail_fast
        self._subscribers: dict[type[BaseMessage], list[Processor]] = {}
        self._processors: list[Processor] = []
        # These will be initialized in the running loop
        self._queue = asyncio.Queue[BaseMessage]()
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stopping = threading.Event()
        self._displaced_signal_handlers: dict[signal.Signals, SignalHandler] = {}
        self._interrupted = False
        self._shutdown_request: ShutdownRequest | None = None

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

    @property
    def stopping(self) -> bool:
        """Whether the bus has begun shutting down, readable from any thread."""
        return self._stopping.is_set()

    @property
    def shutdown_request(self) -> ShutdownRequest | None:
        """The first shutdown request, or ``None`` while no request has been made."""
        return self._shutdown_request

    def register_processor[T: BaseMessage](self, processor: Processor[T], message_types: list[type[T]]):
        """Registers a processor to receive specific message types."""
        processor.bus = self
        for msg_type in message_types:
            self._subscribers.setdefault(msg_type, []).append(processor)
        # By identity: a subclass defining `__eq__` would otherwise drop a distinct processor.
        if not any(registered is processor for registered in self._processors):
            self._processors.append(processor)

    def install_signal_handlers(self) -> None:
        """Route :data:`SHUTDOWN_SIGNALS` to :meth:`on_shutdown_signal` for the life of the run.

        Called by :meth:`initialize`. Override to handle a different set, or to do nothing where the
        process has another owner for them.

        One handler per signal, despite the name: this replaces whatever was installed rather than
        chaining onto it, so two buses in a process would leave only the second one hearing anything.
        For SIGINT what it replaces is the handler that raises ``KeyboardInterrupt``, which is what
        makes shutdown take the same path whichever signal comes first. Whatever is displaced is put
        back by :meth:`remove_signal_handlers`.
        """
        loop = asyncio.get_running_loop()
        for received in SHUTDOWN_SIGNALS:
            displaced = signal.getsignal(received)
            try:
                loop.add_signal_handler(received, self.on_shutdown_signal, received)
            except (NotImplementedError, RuntimeError) as e:
                # Windows loops cannot do this at all, and no loop can off the main thread. Neither is
                # worth failing a run over: the bus still stops, just not on a signal.
                self._logger.debug("Not handling %s: %s", received.name, e)
            else:
                # Recorded only once installed, so a partial install cannot have teardown write back a
                # handler this never displaced.
                self._displaced_signal_handlers[received] = displaced

    def remove_signal_handlers(self) -> None:
        """Undo :meth:`install_signal_handlers`. Called by :meth:`finalize`.

        ``remove_signal_handler`` restores the interpreter default rather than what was displaced, so a
        run would otherwise leave a caller that had its own handler without one.
        """
        loop = asyncio.get_running_loop()
        while self._displaced_signal_handlers:
            received, displaced = self._displaced_signal_handlers.popitem()
            with contextlib.suppress(NotImplementedError, RuntimeError):
                loop.remove_signal_handler(received)
            # None means the handler was not installed from Python, which `signal` refuses to take back.
            if displaced is not None:
                signal.signal(received, displaced)

    def on_shutdown_signal(self, received: signal.Signals) -> None:
        """React to a shutdown signal by winding the bus down.

        Runs as a loop callback rather than in signal context, so it may not block or await. Anything it
        raises reaches the loop's exception handler, and a second signal will not retry it, so put what
        must happen first. Override to add to this, calling ``super()``.
        """
        self._interrupted = self._interrupted or received == signal.SIGINT
        self._logger.warning("Received %s: the bus will wind down", received.name)
        self.request_shutdown(ShutdownRequest.cancelled())

    def request_shutdown(self, request: ShutdownRequest) -> bool:
        """Record the first shutdown request and notify processors once.

        Return ``True`` if accepted, or ``False`` if shutdown was already requested.
        Safe to call from any thread.
        """
        # Never release the claim; repeated or reentrant requests must return without waiting.
        if not self._stop_claim.acquire(blocking=False):
            return False

        self._shutdown_request = request
        self._stopping.set()
        self._logger.info("Stop requested; the bus will wind down")
        self._notify_processors_of_stop()
        return True

    def _notify_processors_of_stop(self) -> None:
        for processor in self._processors:
            try:
                processor.on_stop_requested()
            except Exception as e:
                # Swallowed rather than routed: the caller may be a signal handler, where raising loses
                # the processors behind this one.
                self._logger.error("on_stop_requested failed for '%s': %s", processor.name, e, exc_info=e)

    def submit_message(self, message: BaseMessage):
        """Adds a message to the queue, from any thread.

        ``asyncio.Queue`` is not thread-safe, and a put it loses leaves the bus spinning on a message
        it never reads, so while the bus runs the loop thread makes every put.
        """
        if self.stopping:
            # Dropped rather than raised: processors submit from `finally` blocks, where raising would
            # route an expected shutdown through the error policy.
            self._logger.warning("Dropped %s(%s): the bus is shutting down", type(message).__name__, message.id)
            return

        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._queue.put_nowait, message)
        else:
            self._queue.put_nowait(message)

    def run(self, *, propagate_keyboard_interrupt: bool = False):
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

        Args:
            propagate_keyboard_interrupt: Re-raise ``KeyboardInterrupt`` after a run interrupted by
                SIGINT has wound down. Handling the signal is what stops the interpreter raising it, and
                with it whatever the caller does about one, such as Click's abort. Off by default: a bus
                that wound down cleanly has not failed. Callers that read state off the bus afterwards,
                or report the outcome themselves, want it off.
        """
        asyncio.run(self._entry_point())
        if self._interrupted and propagate_keyboard_interrupt:
            raise KeyboardInterrupt

    async def _entry_point(self) -> None:
        pending_error: BaseException | None = None
        finalization_error: BaseException | None = None
        pending_context = "initialization"
        try:
            await self.initialize()
            pending_context = "message processing"
            await self.process_messages()
        except asyncio.CancelledError as error:
            self.request_shutdown(ShutdownRequest.cancelled())
            pending_error = error
        except Exception as error:
            self.request_shutdown(ShutdownRequest.failed(error))
            pending_error = error
        except BaseException:
            # Finalize before propagating other BaseException subclasses.
            await self.finalize(None)
            raise

        exception = self._primary_failure()
        if exception is None and isinstance(pending_error, Exception):
            exception = pending_error
        try:
            await self.finalize(exception)
        except (asyncio.CancelledError, Exception) as error:
            finalization_error = error

        # Select after finalization, outside exception handlers, to preserve the original chain.
        primary = self._primary_failure()
        if primary is not None:
            if pending_error is not None:
                self._record_secondary_failure(pending_error, primary, secondary_context=pending_context)
            if finalization_error is not None and finalization_error is not pending_error:
                self._record_secondary_failure(finalization_error, primary, secondary_context="finalization")
            raise primary
        if finalization_error is not None:
            if pending_error is not None:
                self._record_secondary_failure(pending_error, finalization_error, secondary_context=pending_context)
            raise finalization_error
        if pending_error is not None:
            raise pending_error

    def _primary_failure(self) -> Exception | None:
        """Return the first accepted failure, if any."""
        request = self.shutdown_request
        if request is not None and request.kind is ShutdownKind.FAILED:
            return request.error
        return None

    def _record_secondary_failure(
        self, secondary: BaseException, primary: BaseException, *, secondary_context: str
    ) -> None:
        """Log the secondary traceback and attach a note without changing the primary's chain."""
        if secondary is primary:
            return
        diagnostic = secondary
        if isinstance(secondary, (MessageProcessingError, OrchestratorHookError, ProcessorHookError)):
            if secondary.original_exception is primary:
                return
            # An interrupted handler may leave its wrapper unraised.
            if secondary.__traceback__ is None:
                diagnostic = secondary.original_exception
        self._logger.error("Secondary exception during %s: %s", secondary_context, secondary, exc_info=diagnostic)
        primary.add_note(f"Additional exception during {secondary_context}: {secondary!r}")

    async def initialize(self):
        """
        Initializes the orchestrator.
        """
        self._running = True
        # Initialization must also respond to shutdown signals.
        self.install_signal_handlers()
        try:
            await self._bounded_by_stop(self.on_initialize(), HookName.ON_INITIALIZE)
        except (FatalProcessingError, asyncio.CancelledError):
            raise
        except Exception as e:
            await self._apply_error_policy(
                OrchestratorHookError(HookName.ON_INITIALIZE, e),
                self.on_error,
            )
        # Keep initialization submissions synchronous so they precede the queue's idle check.
        self._loop = asyncio.get_running_loop()

    @abstractmethod
    async def on_initialize(self):  # pragma: no cover
        """
        Hook for subclasses to perform initial setup (e.g. submit initial messages).

        Shutdown cancels a pending hook. Finalization must tolerate partial initialization.
        """
        pass

    async def finalize(self, exception: Exception | None):
        """
        Method called at the end of the execution lifecycle when all processors have been completed.

        In the case that the execution failed, the exception will be passed to the method
        """
        self._running = False
        self._stopping.set()
        try:
            # Finalization must observe settled processor state.
            await self._drain_executor()
            # A failure may have been recorded while draining.
            primary = self._primary_failure()
            if primary is not None:
                exception = primary
            try:
                await self.on_finalize(exception)
            except (FatalProcessingError, asyncio.CancelledError):
                raise
            except Exception as error:
                await self._apply_error_policy(
                    OrchestratorHookError(HookName.ON_FINALIZE, error),
                    self.on_error,
                )
        finally:
            # Restore handlers even if executor draining is interrupted.
            self.remove_signal_handlers()

    async def _run_in_worker[T: BaseMessage](self, work: Callable[[T], None], message: T) -> None:
        """Track the executor future because cancelling its awaiter cannot stop a running thread.

        Executor submission does not propagate contextvars; each invocation needs its own copy.
        """
        context = contextvars.copy_context()
        future = self._executor.submit(context.run, work, message)
        with self._sync_work_lock:
            self._sync_work.add(future)
        future.add_done_callback(self._forget_sync_work)
        await asyncio.wrap_future(future)

    def _forget_sync_work(self, future: Future) -> None:
        """Drop work that has finished, called by the pool thread that finished it."""
        with self._sync_work_lock:
            self._sync_work.discard(future)

    def _pending_sync_work(self) -> set[Future]:
        """Copy pending work under the lock; worker callbacks modify the set concurrently."""
        with self._sync_work_lock:
            in_flight = set(self._sync_work)

        return {future for future in in_flight if not future.done()}

    async def _drain_executor(self) -> None:
        """Wait for our sync work, including work on a borrowed executor.

        Running threads cannot be cancelled, so finalization must wait for them.
        Shut down the executor only if we own it.
        """
        pending = self._pending_sync_work()
        if pending:
            self._logger.debug("Waiting for %s sync processor(s) still running...", len(pending))
            await asyncio.to_thread(wait_for_futures, pending)

        if self._owns_executor:
            self._logger.debug("Retiring the processor thread pool...")
            await asyncio.to_thread(self._executor.shutdown, wait=True)

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

        Returning cleanly proceeds with dispatching the message to every processor
        whose ``should_process_message`` accepts it. To prevent dispatch for this
        message specifically, raise :class:`SkipMessageError` directly from this
        hook. To stop the bus entirely, raise :class:`FatalProcessingError`. Any
        other exception is wrapped as :class:`OrchestratorHookError` and routed
        through :meth:`on_error`.

        Shutdown cancels a pending hook without dispatching the message.
        """
        pass

    async def on_error(self, error: OrchestratorHookError) -> None:
        """
        Handle an orchestrator-scoped failure.

        Called when ``on_initialize``, ``on_message_received``, or ``on_finalize``
        raises a non-Fatal exception. ``error`` is always an
        :class:`OrchestratorHookError` whose ``.hook_name`` and ``.original_exception``
        identify what failed.

        Behavior of the return:
          - Return cleanly: the error is considered handled, processing continues.
          - Raise :class:`FatalProcessingError`: stop the orchestrator.
          - Raise anything else: the orchestrator's ``fail_fast`` policy decides.

        The default implementation re-raises so unmodified orchestrators fall through
        to the ``fail_fast`` policy.

        Shutdown cancels pending recovery. A handler started after a shutdown request
        gets one scheduling turn to complete; otherwise ``fail_fast`` applies.
        """
        raise error

    async def _apply_error_policy[E: Exception](self, wrapped_error: E, handler: ErrorHandler[E]) -> None:
        """Apply the handler and ``fail_fast`` policy described by :meth:`on_error`.

        Orchestrator handlers need shutdown-aware waits. Processor handlers are
        cancelled with their tracked processing tasks.
        """
        hook_name = getattr(wrapped_error, "hook_name", type(wrapped_error).__name__)
        try:
            if isinstance(wrapped_error, OrchestratorHookError):
                handled = await self._bounded_by_stop(
                    handler(wrapped_error),
                    HookName.ON_ERROR,
                    start_when_stopping=True,
                )
            else:
                await handler(wrapped_error)
                return
        except (FatalProcessingError, asyncio.CancelledError):
            raise
        except Exception as e:
            if self._fail_fast:
                raise
            if (primary := self._primary_failure()) is not None:
                self._record_secondary_failure(e, primary, secondary_context=f"on_error handling {hook_name}")
                return
            self._logger.error(
                "on_error handler for '%s' raised %s while processing %s",
                hook_name,
                e,
                wrapped_error,
            )
            return
        if handled:
            return
        # An interrupted handler has not recovered from the original error.
        if self._fail_fast:
            raise wrapped_error
        if (primary := self._primary_failure()) is not None:
            self._record_secondary_failure(wrapped_error, primary, secondary_context=f"on_error handling {hook_name}")
            return
        self._logger.error(
            "Shutdown interrupted on_error for '%s'; unhandled error: %s",
            hook_name,
            wrapped_error,
        )

    def _remaining_time(self, start_time: float) -> float:
        """
        Calculates the remaining time until the max timeout is reached.

        Returns ``math.inf`` when running unbounded.
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
        cancel_reason: str | None = None

        try:
            while not await self.__should_stop(start_time, running_tasks, get_task):
                wait_set = running_tasks | {get_task}
                # We use a small timeout to check for max_timeout periodically. If we leave this here blocking
                # we can keep the loop alive much longer than the max_timeout.
                done, _ = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED, timeout=STOP_CHECK_INTERVAL)

                current_get_task = get_task
                if current_get_task in done:
                    get_task = await self.__process_new_message(current_get_task, running_tasks)
                    if get_task is None:
                        break

                self.__process_finished_tasks(done, current_get_task, running_tasks)
        except OrchestratorTimeout as timeout:
            # Recorded before the drain below, so finalization knows this exit for what it is.
            self.request_shutdown(ShutdownRequest.timed_out(timeout))
            cancel_reason = str(timeout)
        except asyncio.CancelledError:
            # Notify processors before draining a cancelled bus.
            self.request_shutdown(ShutdownRequest.cancelled())
            raise
        except Exception as error:
            # The error policy has already decided this error stops the bus.
            self.request_shutdown(ShutdownRequest.failed(error))
            raise
        finally:
            # If we exit the loop and tasks are still running (e.g. timeout or forced break),
            # we must clean them up before returning to ensure finalize() runs in a safe state.
            # This is the single place that cancels ``running_tasks``, so every remaining task
            # is cancelled exactly once, with the reason (if any) attached.
            if running_tasks:
                self._logger.info("Cancelling %s remaining tasks...", len(running_tasks))
                for task in running_tasks:
                    task.cancel(cancel_reason)

                # Wait for them to actually finish cancelling
                await asyncio.wait(running_tasks)

            # Also ensure the get_task is dead if it's still around
            if get_task and not get_task.done():
                get_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await get_task

    async def __should_stop(self, start_time: float, running_tasks: set[asyncio.Task], get_task: asyncio.Task) -> bool:
        """
        Checks whether the orchestrator should stop. This can happen in three ways:
        - A stop was requested
        - The max timeout is reached
        - The queue is empty and all processors have been completed and the grace period is reached
        """
        # First, because a caller asking to stop outranks reporting a timeout it did not wait for.
        if self.stopping:
            self._logger.info(
                "Stopping on request. A total of %s tasks were running.",
                len(running_tasks),
            )
            get_task.cancel()
            return True

        # Check first whether we are over the max timeout
        if self._remaining_time(start_time) <= 0:
            self._logger.error(
                "Orchestrator timed out after %s seconds. A total of %s tasks were running.",
                self._max_timeout,
                len(running_tasks),
            )
            get_task.cancel()
            raise OrchestratorTimeout(f"Orchestrator exceeded max_timeout of {self._max_timeout}s")

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
                if not await self.__wait_for_message(get_task, wait_time):
                    if self.stopping:
                        # Said here too, or a stop seen inside the wait leaves through this branch and
                        # reads like the grace period simply expiring.
                        self._logger.info("Stopping on request while idle.")
                    get_task.cancel()
                    return True
            except Exception:
                # If the get_task failed, we return False to let the loop handle the exception
                return False

        return False

    async def _bounded_by_stop(
        self,
        hook: Awaitable[None],
        name: HookName,
        *,
        start_when_stopping: bool = False,
    ) -> bool:
        """Own the hook task until completion or cancellation; return False if stopped early.

        ``start_when_stopping`` allows normal finalization recovery and gives error
        handlers one scheduling turn when shutdown has already been requested.
        The hook must cooperate with cancellation before this wait can finish.
        """
        work = asyncio.ensure_future(hook)
        retrieved = False
        one_turn = start_when_stopping and self.shutdown_request is not None
        try:
            while True:
                # Normal finalization sets stopping without requesting shutdown.
                should_cancel = self.stopping if not start_when_stopping else self.shutdown_request is not None
                if should_cancel and not one_turn:
                    self._logger.warning("Abandoned %s: a stop was requested", name)
                    return False
                done, _ = await asyncio.wait({work}, timeout=0 if one_turn else STOP_CHECK_INTERVAL)
                if done:
                    retrieved = True
                    await work
                    return True
                one_turn = False
        except asyncio.CancelledError:
            # Notify processors before draining the cancelled hook.
            self.request_shutdown(ShutdownRequest.cancelled())
            raise
        finally:
            if not retrieved:
                if not work.done():
                    work.cancel()
                try:
                    await work
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    if (primary := self._primary_failure()) is not None:
                        self._record_secondary_failure(e, primary, secondary_context=f"{name} cleanup")
                    else:
                        self._logger.error("Abandoned %s raised %s", name, e, exc_info=e)

    async def __wait_for_message(self, get_task: asyncio.Task, wait_time: float) -> bool:
        """Whether a message arrived within ``wait_time``.

        Waited out in slices rather than in one go, so a stop requested while the bus sits idle is
        acted on promptly instead of after a grace period that can be far longer than the caller has.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + wait_time
        while (remaining := deadline - loop.time()) > 0:
            if self.stopping:
                return False
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(get_task), timeout=min(STOP_CHECK_INTERVAL, remaining))
                return True

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

        # If we successfully got a message, process it. SkipMessageError raised
        # directly from on_message_received skips dispatch for this message and
        # continues with the next one.
        try:
            await self._bounded_by_stop(self.on_message_received(msg), HookName.ON_MESSAGE_RECEIVED)
        except (asyncio.CancelledError, FatalProcessingError):
            raise
        except SkipMessageError as e:
            self._logger.warning("Skipping message %s: %s", msg.id, e)
            return asyncio.create_task(self._queue.get())
        except Exception as e:
            await self._apply_error_policy(
                OrchestratorHookError(HookName.ON_MESSAGE_RECEIVED, e, message=msg),
                self.on_error,
            )

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
        # Tasks that escape with an exception have already been through their processor's
        # on_error and the orchestrator's policy. The escape itself means the policy
        # decided to stop the bus, so propagate the first failure to finalize().
        # FIRST_COMPLETED can deliver several failed tasks in one batch; log the rest
        # so post-mortems aren't single-task views of multi-task failures.
        first_exc: BaseException | None = None
        for task in done:
            if task is get_task:
                continue
            running_tasks.discard(task)
            if task.cancelled():
                continue
            exc = task.exception()
            if exc is None:
                continue
            if first_exc is None:
                first_exc = exc
            else:
                self._logger.error("Additional task failure suppressed: %s", exc)
        if first_exc is not None:
            raise first_exc

    def _handle_message(self, msg: BaseMessage, running_tasks: set[asyncio.Task]):
        """
        Launches asyncio tasks to process the given message by any processors that are subscribed to the message type.

        The `running_tasks` set is updated with the processors that have been launched.
        """
        running_tasks.update(
            asyncio.create_task(self._task_wrapper(processor, msg))
            for processor in self._subscribers.get(type(msg), [])
            if processor.should_process_message(msg)
        )

    async def _task_wrapper(self, processor: Processor, message: BaseMessage):
        """
        Processes a message by the given processor.

        Routes any process_message failure (wrapped as :class:`MessageProcessingError`)
        and any on_success failure (wrapped as :class:`ProcessorHookError`)
        through the processor's ``on_error`` and applies the orchestrator's policy.
        """
        if self.stopping:
            # A task can be created before the stop and scheduled after it, so refusing here covers
            # every processor without each having to check.
            self._logger.warning(
                "Not dispatching %s(%s) to %s: the bus is shutting down",
                type(message).__name__,
                message.id,
                processor.name,
            )
            return

        scope = self._message_scope(message) if self._message_scope is not None else nullcontext()
        with scope:
            try:
                match processor:
                    case AsyncProcessor():
                        await cast(AsyncProcessor, processor).process_message(message)
                    case SyncProcessor():
                        await self._run_in_worker(processor.process_message, message)
                    case _:
                        assert_never(processor)
            except (FatalProcessingError, asyncio.CancelledError):
                raise
            except Exception as processing_error:
                await self._apply_error_policy(
                    MessageProcessingError(processor.name, message, processing_error),
                    processor.on_error,
                )
                return

            try:
                await processor.on_success(message)
            except (FatalProcessingError, asyncio.CancelledError):
                raise
            except Exception as e:
                await self._apply_error_policy(
                    ProcessorHookError(HookName.ON_SUCCESS, processor.name, message, e),
                    processor.on_error,
                )
