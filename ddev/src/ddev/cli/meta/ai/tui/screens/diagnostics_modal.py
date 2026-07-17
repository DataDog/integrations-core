# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Static

from ddev.ai.config.errors import FlowError
from ddev.ai.config.models import FlowResult


class FlowDiagnosticsModal(ModalScreen[None]):
    """Read-only details for a flow that could not be resolved."""

    BINDINGS = [Binding("escape", "dismiss_modal", "Close")]

    def __init__(self, result: FlowResult) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="diagnostics")
        dialog.border_title = f"diagnostics · {self.result.name}"
        with dialog:
            yield Static("This flow cannot be launched until these configuration errors are fixed.", classes="desc")
            with VerticalScroll(id="diagnostic-errors"):
                for index, error in enumerate(self.result.errors, start=1):
                    yield self._error_widget(index, error)
            with Horizontal(classes="modal-actions"):
                yield Button("Close", id="btn-close", variant="primary")

    def _error_widget(self, index: int, error: FlowError) -> Widget:
        details = Text(f"{index:02d} · {error.kind.value}", style="bold")
        details.append(f"\n{error.message}")
        context = []
        if error.phase:
            context.append(f"phase: {error.phase}")
        if error.subject:
            context.append(f"subject: {error.subject}")
        if context:
            details.append("\n" + " · ".join(context), style="dim")
        if error.sources:
            details.append("\nsources:", style="dim")
            for source in error.sources:
                details.append(f"\n  {source}")
        return Static(details, classes="diagnostic-error")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(None)
