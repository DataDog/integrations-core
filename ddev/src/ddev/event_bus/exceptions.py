# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import BaseMessage


class ProcessorQueueError(Exception):
    """
    Exception raised when a processor queue is not initialized.
    """

    pass


class MessageProcessingError(Exception):
    """
    Exception raised when a processor fails to process a message.
    """

    def __init__(self, processor_name: str, message: BaseMessage, original_exception: Exception):
        self.processor_name = processor_name
        self.message = message
        self.original_exception = original_exception
        super().__init__(
            f"Error processing message by processor '{processor_name}'. "
            f"Message: {message}. Original error: {original_exception}"
        )


class ProcessorSuccessHookError(MessageProcessingError):
    """
    Exception raised when the on_success hook of a processor fails.
    """

    def __init__(self, processor_name: str, message: BaseMessage, original_exception: Exception):
        super(Exception, self).__init__(
            f"Error in 'on_success' hook for processor '{processor_name}'. "
            f"Message: {message}. "
            f"Original error: {original_exception}"
        )
        self.processor_name = processor_name
        self.message = message
        self.original_exception = original_exception
