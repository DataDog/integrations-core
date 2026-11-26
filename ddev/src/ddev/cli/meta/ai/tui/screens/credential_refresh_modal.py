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
from ddev.ai.runtime.login_prompt import LoginAction, LoginProblem


class LoginRecoveryModal(ModalScreen[LoginAction]):
    AUTO_FOCUS = "#btn-retry"
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, problem: LoginProblem) -> None:
        super().__init__()
        self._problem = problem

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="phase-error")
        dialog.border_title = self._problem.title
        with dialog:
            with VerticalScroll(id="phase-error-details"):
                yield Static(
                    f"{self._problem.instructions}\n\nChoose Retry to try again or Cancel to stop the run.",
                    id="credential-refresh-message",
                    markup=False,
                )
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Retry", id="btn-retry", variant="primary")

    def action_cancel(self) -> None:
        self.dismiss(LoginAction.CANCEL)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-retry":
            self.dismiss(LoginAction.RETRY)
        elif event.button.id == "btn-cancel":
            self.action_cancel()


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
