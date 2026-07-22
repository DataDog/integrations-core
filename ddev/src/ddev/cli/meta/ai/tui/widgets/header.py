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

EXECUTION_STATUS_TEXT = {
    ExecutionStatus.IDLE: "",
    ExecutionStatus.RUNNING: "● running",
    ExecutionStatus.FINISHING: "◌ finishing",
    ExecutionStatus.COMPLETED: "✓ completed",
    ExecutionStatus.FAILED: "✕ failed",
}


class ExecutionStatusBadge(Static):
    """Render the current app-wide execution status."""

    execution_status: reactive[ExecutionStatus] = reactive(ExecutionStatus.IDLE, init=False)

    def on_mount(self) -> None:
        self.watch(cast("TogoApp", self.app), "execution_status", self._sync_execution_status)

    def watch_execution_status(self, old_status: ExecutionStatus, new_status: ExecutionStatus) -> None:
        self.toggle_class(f"status-{old_status.value}", f"status-{new_status.value}")
        self.update(EXECUTION_STATUS_TEXT[new_status])

        if new_status is ExecutionStatus.RUNNING:
            self._pulse_down()
        else:
            self.styles.animate("text_opacity", 1.0, duration=0.2)

    def _sync_execution_status(self, status: ExecutionStatus) -> None:
        self.execution_status = status

    def _pulse_down(self) -> None:
        if self.execution_status is not ExecutionStatus.RUNNING or self.app.animation_level != "full":
            return
        self.styles.animate(
            "text_opacity",
            0.35,
            duration=0.8,
            easing="in_out_sine",
            on_complete=self._pulse_up,
        )

    def _pulse_up(self) -> None:
        if self.execution_status is not ExecutionStatus.RUNNING or self.app.animation_level != "full":
            return
        self.styles.animate(
            "text_opacity",
            1.0,
            duration=0.8,
            easing="in_out_sine",
            on_complete=self._pulse_down,
        )


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
        yield ExecutionStatusBadge(id="header-right", classes="status-idle")

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
