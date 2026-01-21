# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .orchestrator import BaseMessage


class TaskQueueError(Exception):
    """
    Exception raised when a task queue is not initialized.
    """

    pass


class TaskProcessingError(Exception):
    """
    Exception raised when a task fails to process a message.
    """

    def __init__(self, task_name: str, message: BaseMessage, original_exception: Exception):
        self.task_name = task_name
        self.message = message
        self.original_exception = original_exception
        super().__init__(
            f"Error processing message by task '{task_name}'. Message: {message}. Original error: {original_exception}"
        )


class TaskSuccessHookError(TaskProcessingError):
    """
    Exception raised when the on_success hook of a task fails.
    """

    def __init__(self, task_name: str, message: BaseMessage, original_exception: Exception):
        super(Exception, self).__init__(
            f"Error in 'on_success' hook for task '{task_name}'. "
            f"Message: {message}. "
            f"Original error: {original_exception}"
        )
        self.task_name = task_name
        self.message = message
        self.original_exception = original_exception
