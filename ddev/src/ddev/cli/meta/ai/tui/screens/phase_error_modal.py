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

from ddev.cli.meta.ai.palette import ERROR


class PhaseErrorModal(ModalScreen[None]):
    """Show the complete error for a failed phase over the execution view."""

    AUTO_FOCUS = "#btn-close"
    BINDINGS = [Binding("escape", "dismiss_modal", "Close")]

    def __init__(self, phase_id: str, error: BaseException) -> None:
        super().__init__()
        self.phase_id = phase_id
        self.error = error

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="phase-error")
        dialog.border_title = f"Phase failed · {self.phase_id}"
        with dialog:
            yield Static("The complete phase error is shown below.", classes="desc")
            with VerticalScroll(id="phase-error-details"):
                message = Text(f"{type(self.error).__name__}: ", style=f"bold {ERROR}")
                message.append(str(self.error))
                yield Static(message, id="phase-error-message")
            with Horizontal(classes="modal-actions"):
                yield Button("Close", id="btn-close", variant="primary")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.dismiss(None)
