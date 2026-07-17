# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""TogoHeader widget — wordmark, screen title, optional running badge, clock."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ddev.ai.config.models import ConfigStatus
from ddev.cli.meta.ai.palette import ERROR, PRIMARY

if TYPE_CHECKING:
    from ddev.cli.meta.ai.tui.app import TogoApp

TOGO_HUSKY = """█▀▄     ▄▀█
███████████
██ ▀ █ ▀ ██
█▀▄▄▄█▄▄▄▀█
  ▀▀███▀▀"""


class TogoHeader(Widget):
    """App header with the Togo mascot, flow summary, repository, and run state."""

    DEFAULT_CSS = ""

    running: reactive[bool] = reactive(False)
    _pulse_on: reactive[bool] = reactive(True)

    def __init__(self, title: str = "", running: bool = False) -> None:
        super().__init__()
        self._title = title
        self.running = running

    def compose(self) -> ComposeResult:
        yield Static(TOGO_HUSKY, id="header-mascot")
        with Vertical(id="header-info"):
            product = Text("Togo", style=f"bold {PRIMARY}")
            product.append(" ◆ Agent Integrations")
            yield Static(product, id="header-product")
            yield Static("", id="header-flow-summary")
            yield Static("", id="header-repo")
        yield Static("", id="header-right")

    def on_mount(self) -> None:
        self.set_interval(0.6, self._tick_pulse)
        self._update_context()
        self._update_running_badge()

    def watch_running(self, running: bool) -> None:
        self._update_running_badge()

    def watch__pulse_on(self, pulse_on: bool) -> None:
        self._update_running_badge()

    def _tick_pulse(self) -> None:
        if self.running:
            self._pulse_on = not self._pulse_on

    def _update_context(self) -> None:
        app = cast("TogoApp", self.app)
        results = app.engine.flows.values()
        broken_count = sum(result.status is ConfigStatus.BROKEN for result in results)
        summary = Text(f"{len(app.engine.flows)} Flows Discovered")
        if broken_count:
            summary.append(f" / {broken_count} flows need attention", style=ERROR)
        self.query_one("#header-flow-summary", Static).update(summary)
        self.query_one("#header-repo", Static).update(str(app.ddev_app.repo.path))

    def _update_running_badge(self) -> None:
        try:
            right = self.query_one("#header-right", Static)
        except Exception:
            return
        if not self.running:
            right.update("")
            return
        marker = "●" if self._pulse_on else "○"
        right.update(f"{marker} running")
