# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.ai.agent.types import StopReason


class AgentError(Exception):
    """Base class for all errors raised by an agent."""


class IncompleteResponseError(AgentError):
    """A turn that was required to complete ended without END_TURN
    (e.g. truncated by max_tokens, or an abnormal stop reason)."""

    def __init__(self, message: str, *, stop_reason: StopReason):
        super().__init__(message)
        self.stop_reason = stop_reason


class AgentConnectionError(AgentError):
    """Network failure — the API was unreachable."""


class AgentRateLimitError(AgentError):
    """Rate limit hit — the request may be retried after a delay."""


class AgentAPIError(AgentError):
    """The API returned an error status code."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
