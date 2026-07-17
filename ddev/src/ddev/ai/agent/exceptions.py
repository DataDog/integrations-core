# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio


def describe_agent_error(error: BaseException) -> str:
    """Human-readable description of an error raised while running an agent.

    The orchestrator cancels in-flight agent tasks with a message when it stops
    them because ``max_timeout`` was exceeded, rather than because of a genuine
    failure. Surface that as a timeout instead of a bare ``CancelledError``.
    """
    if isinstance(error, asyncio.CancelledError) and str(error):
        return f"Timed out: {error}"
    return f"{type(error).__name__}: {error}"


class AgentError(Exception):
    """Base class for all errors raised by an agent."""


class AgentConnectionError(AgentError):
    """Network failure — the API was unreachable."""


class AgentRateLimitError(AgentError):
    """Rate limit hit — the request may be retried after a delay."""


class AgentAPIError(AgentError):
    """The API returned an error status code."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
