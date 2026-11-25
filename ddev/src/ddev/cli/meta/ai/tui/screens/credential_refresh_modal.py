# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Static

from ddev.ai.runtime.errors import CredentialRefreshError


class CredentialRefreshModal(ModalScreen[None]):
    AUTO_FOCUS = "#btn-close"
    BINDINGS = [Binding("escape", "close", "Close")]

    def __init__(self, error: CredentialRefreshError) -> None:
        super().__init__()
        self._error = error

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="phase-error")
        dialog.border_title = "AI Gateway login failed" if self._error.startup else "Credential refresh failed"
        with dialog:
            with VerticalScroll(id="phase-error-details"):
                yield Static(str(self._error), id="credential-refresh-message", markup=False)
            with Horizontal(classes="modal-actions"):
                yield Button("Close", id="btn-close", variant="primary")

    def action_close(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            self.action_close()
