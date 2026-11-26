# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass

from textual.screen import Screen

from ddev.ai.phases.notices import PhaseStarted
from ddev.ai.run_events import Notice, RunEvents
from ddev.cli.meta.ai.tui.bridge import subscribe_run_notices
from ddev.cli.meta.ai.tui.messages import NoticeMessage


@dataclass(frozen=True)
class Progress(Notice):
    completed: int


class NoticeSink(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.notices: list[Notice] = []

    def on_notice_message(self, message: NoticeMessage) -> None:
        message.stop()
        self.notices.append(message.notice)


async def test_bridge_forwards_any_notice_to_the_current_target(make_togo_app):
    app = make_togo_app([])
    events = RunEvents()
    subscribe_run_notices(events, app)
    started = PhaseStarted("plan")
    progress = Progress(completed=2)

    async with app.run_test() as pilot:
        await events.notify(started)
        await pilot.pause()

        sink = NoticeSink()
        await app.push_screen(sink)
        app.bridge_target = sink
        await events.notify(progress)
        await pilot.pause()

    assert len(app.received) == 1
    assert app.received[0].notice is started
    assert len(sink.notices) == 1
    assert sink.notices[0] is progress
