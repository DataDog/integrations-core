# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable
from pathlib import Path

import httpx

TARGET = "http://localhost:4200"


class RecordingTransport(httpx.MockTransport):
    """MockTransport that keeps every request it was asked to send."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []

        def record(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return handler(request)

        super().__init__(record)


def respond(response: httpx.Response) -> RecordingTransport:
    return RecordingTransport(lambda request: response)


def saved_files(root: Path) -> list[Path]:
    """Every file below `root`, including leftover partial files."""
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
