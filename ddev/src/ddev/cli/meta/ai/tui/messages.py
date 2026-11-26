# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Messages local to the Textual interface."""

from textual.message import Message

from ddev.ai.run_events import Notice


class NoticeMessage(Message):
    """Carry a run notice to the active Textual target."""

    def __init__(self, notice: Notice) -> None:
        super().__init__()
        self.notice = notice


class ExecutionFailed(Message):
    """Fired when execution exits through an unexpected exception."""

    def __init__(self, error: BaseException) -> None:
        super().__init__()
        self.error = error
