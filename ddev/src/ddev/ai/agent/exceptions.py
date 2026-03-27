# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class AgentError(Exception):
    """Base class for all errors raised by AnthropicAgent."""

    pass


class AgentConnectionError(AgentError):
    """Network failure — the API was unreachable."""

    pass


class AgentRateLimitError(AgentError):
    """Rate limit hit — the request may be retried after a delay."""

    pass


class AgentAPIError(AgentError):
    """The API returned an error status code."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
