# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import stamina

if TYPE_CHECKING:
    from collections.abc import Callable

# Failures that say nothing about what the server would have served: the connection was
# refused, timed out, or was reset before a complete response arrived. Windows CI runners
# in particular reset connections mid-handshake (`[WinError 10054]`, a `ConnectError`).
TRANSIENT_ERRORS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)

REQUEST_ATTEMPTS = 3


@stamina.retry(on=TRANSIENT_ERRORS, attempts=REQUEST_ATTEMPTS)
def request_with_retries[T](send: Callable[[], T]) -> T:
    """Call `send`, retrying transient connection failures with backoff.

    Only connection-level failures are retried, and the last one propagates once the
    attempts are spent. A response the server actually served is handed straight back, so
    a real 404 is never retried as if it were a network blip.

    `send` is replayed wholesale, so it must be safe to repeat: a read against an
    idempotent endpoint qualifies, a mutation does not.
    """
    return send()


def download_file(path, *args, **kwargs):
    with path.open(mode='wb', buffering=0) as f:
        with httpx.stream('GET', *args, **kwargs) as response:
            for chunk in response.iter_bytes(16384):
                f.write(chunk)
