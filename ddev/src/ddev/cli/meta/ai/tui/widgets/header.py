# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""TogoHeader widget — wordmark, flow context, and execution badge."""

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
from ddev.cli.meta.ai.tui.status import ExecutionStatus

if TYPE_CHECKING:
    from ddev.cli.meta.ai.tui.app import TogoApp

TOGO_HUSKY = """█▀▄     ▄▀█
███████████
██ ▀ █ ▀ ██
█▀▄▄▄█▄▄▄▀█
  ▀▀███▀▀"""

EXECUTION_STATUS_CLASSES = (
    "status-running",
    "status-finishing",
    "status-completed",
    "status-failed",
)


class ExecutionStatusBadge(Static):
    """Render the current app-wide execution status."""

    _pulse_on: reactive[bool] = reactive(True)

    def on_mount(self) -> None:
        self.watch(self.app, "execution_status", self._watch_execution_status)
        self.set_interval(0.6, self._tick_pulse)

    def render(self) -> str:
        status = cast("TogoApp", self.app).execution_status
        if status is ExecutionStatus.IDLE:
            return ""
        if status is ExecutionStatus.RUNNING:
            marker = "●" if self._pulse_on else "○"
            return f"{marker} running"
        return {
            ExecutionStatus.FINISHING: "◌ finishing",
            ExecutionStatus.COMPLETED: "✓ completed",
            ExecutionStatus.FAILED: "✕ failed",
        }[status]

    def watch__pulse_on(self) -> None:
        self.refresh()

    def _watch_execution_status(self, status: ExecutionStatus) -> None:
        self.remove_class(*EXECUTION_STATUS_CLASSES)
        if status is not ExecutionStatus.IDLE:
            self.add_class(f"status-{status.value}")
        self.refresh(layout=True)

    def _tick_pulse(self) -> None:
        if cast("TogoApp", self.app).execution_status is ExecutionStatus.RUNNING:
            self._pulse_on = not self._pulse_on


class TogoHeader(Widget):
    """App header with the Togo mascot, flow summary, repository, and run state."""

    DEFAULT_CSS = ""

    def __init__(self, title: str = "") -> None:
        super().__init__()
        self._title = title

    def compose(self) -> ComposeResult:
        yield Static(TOGO_HUSKY, id="header-mascot")
        with Vertical(id="header-info"):
            product = Text("Togo", style=f"bold {PRIMARY}")
            product.append(" ◆ Agent Integrations")
            yield Static(product, id="header-product")
            yield Static("", id="header-flow-summary")
            yield Static("", id="header-repo")
        yield ExecutionStatusBadge(id="header-right")

    def on_mount(self) -> None:
        self._update_context()

    def _update_context(self) -> None:
        app = cast("TogoApp", self.app)
        results = app.engine.flows.values()
        broken_count = sum(result.status is ConfigStatus.BROKEN for result in results)
        summary = Text(f"{len(app.engine.flows)} Flows Discovered")
        if broken_count:
            summary.append(f" / {broken_count} flows need attention", style=ERROR)
        self.query_one("#header-flow-summary", Static).update(summary)
        self.query_one("#header-repo", Static).update(str(app.ddev_app.repo.path))
