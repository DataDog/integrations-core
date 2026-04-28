# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import BaseMessage


class HookName(str, Enum):
    """Names of the lifecycle hooks exposed by the event bus."""

    ON_INITIALIZE = "on_initialize"
    ON_FINALIZE = "on_finalize"
    ON_MESSAGE_RECEIVED = "on_message_received"
    ON_SUCCESS = "on_success"
    ON_ERROR = "on_error"


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
    Exception raised when a processor-level hook (``on_success``) fails.
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


class ProcessorSuccessHookError(ProcessorHookError):
    """
    Exception raised when the ``on_success`` hook of a processor fails.
    """

    def __init__(self, processor_name: str, message: BaseMessage, original_exception: Exception):
        super().__init__(HookName.ON_SUCCESS, processor_name, message, original_exception)


class FatalProcessingError(Exception):
    """
    Raised by hooks or processors to signal that the orchestrator should stop
    processing immediately and shut down gracefully.

    This is the explicit "stop the bus" signal — any hook (including ``on_error``)
    can raise it to halt the orchestrator regardless of the ``fail_fast`` policy.
    """

    pass
