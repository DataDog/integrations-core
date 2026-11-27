# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Forward run notices to the active Textual message target."""

from __future__ import annotations

from typing import Protocol

from textual.message_pump import MessagePump

from ddev.ai.run_events import Notice, RunEvents
from ddev.cli.meta.ai.tui.messages import NoticeMessage


class BridgeApp(Protocol):
    @property
    def bridge_target(self) -> MessagePump: ...


def subscribe_run_notices(events: RunEvents, app: BridgeApp) -> None:
    async def forward(notice: Notice) -> None:
        app.bridge_target.post_message(NoticeMessage(notice))

    events.subscribe(Notice, forward, exact=False)
