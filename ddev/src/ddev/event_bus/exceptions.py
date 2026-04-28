# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import BaseMessage


class HookName(StrEnum):
    """Names of the lifecycle hooks exposed by the event bus."""

    ON_INITIALIZE = auto()
    ON_FINALIZE = auto()
    ON_MESSAGE_RECEIVED = auto()
    ON_SUCCESS = auto()


class ProcessorQueueError(Exception):
    """
    Exception raised when a processor queue is not initialized.
    """

    pass


class MessageProcessingError(Exception):
    """
    Exception raised when a processor's ``process_message`` call fails.

    Routed to the processor's ``on_error`` so the developer can decide what to do
    with a per-message failure.
    """

    def __init__(self, processor_name: str, message: BaseMessage, original_exception: Exception):
        self.processor_name = processor_name
        self.message = message
        self.original_exception = original_exception
        super().__init__(
            f"Error processing message by processor '{processor_name}'. "
            f"Message: {message}. Original error: {original_exception}"
        )


class HookExecutionError(Exception):
    """
    Base class for hook execution failures.

    Hook failures are routed to the appropriate ``on_error`` (orchestrator-scope
    or processor-scope) so the developer can decide whether to keep going,
    stop the bus via ``FatalProcessingError``, or let the orchestrator's
    ``fail_fast`` policy decide.
    """

    def __init__(self, hook_name: HookName, original_exception: Exception, description: str):
        self.hook_name = hook_name
        self.original_exception = original_exception
        super().__init__(description)


class OrchestratorHookError(HookExecutionError):
    """
    Exception raised when an orchestrator-level hook (``on_initialize``,
    ``on_message_received``, ``on_finalize``) fails.

    ``message`` is the message being processed when the failure occurred, if any.
    For ``on_initialize`` and ``on_finalize`` failures it will be ``None``.
    """

    def __init__(
        self,
        hook_name: HookName,
        original_exception: Exception,
        message: BaseMessage | None = None,
    ):
        rendered_message = f"Message: {message}. " if message is not None else ""
        super().__init__(
            hook_name,
            original_exception,
            f"Error in '{hook_name.value}' orchestrator hook. {rendered_message}Original error: {original_exception}",
        )
        self.message = message


class ProcessorHookError(HookExecutionError):
    """
    Exception raised when a processor-level hook (e.g. ``on_success``) fails.
    """

    def __init__(
        self,
        hook_name: HookName,
        processor_name: str,
        message: BaseMessage,
        original_exception: Exception,
    ):
        super().__init__(
            hook_name,
            original_exception,
            f"Error in '{hook_name.value}' hook for processor '{processor_name}'. "
            f"Message: {message}. Original error: {original_exception}",
        )
        self.processor_name = processor_name
        self.message = message


class FatalProcessingError(Exception):
    """
    Raised by hooks or processors to signal that the orchestrator should stop
    processing immediately and shut down gracefully.

    This is the explicit "stop the bus" signal. Any hook (including ``on_error``)
    can raise it to halt the orchestrator regardless of the ``fail_fast`` policy.
    """

    pass


class SkipMessageError(Exception):
    """
    Raised directly from ``on_message_received`` to skip dispatch for the current
    message and continue the loop.

    Use this when the orchestrator decides a specific message cannot be processed
    safely and no processor should receive it. Per-processor filtering (when
    *some* processors should still see the message) belongs in
    ``BaseProcessor.should_process_message`` instead.

    Only honored when raised directly from ``on_message_received``. From any other
    hook (``on_initialize``, ``on_finalize``, ``on_error``, processor scope) it
    propagates as a regular exception subject to the ``fail_fast`` policy.
    """

    pass
