# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations


class CatalystApiError(Exception):
    """Raised when Catalyst Center reports a failure, whatever envelope it arrives in.

    ``error_code`` is deliberately untyped: the API returns an integer for validation failures
    (``14001``) and a string for request-level ones (``"Bad request"``).

    ``correlation_id`` is the value of the ``x-correlation-id`` response header. Cisco TAC asks
    for it by name, and it is the only handle they accept when investigating a failed call, so
    it is carried on every error rather than only logged.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: int | str | None = None,
        detail: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.detail = detail
        self.correlation_id = correlation_id
        super().__init__(self._format(message))

    def _format(self, message: str) -> str:
        parts = [message]
        if self.error_code is not None:
            parts.append(f'errorCode={self.error_code}')
        if self.detail:
            parts.append(f'detail={self.detail}')
        if self.correlation_id:
            parts.append(f'x-correlation-id={self.correlation_id}')
        return ' | '.join(parts)
