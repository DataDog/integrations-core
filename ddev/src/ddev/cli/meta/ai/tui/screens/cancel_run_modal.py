# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""CancelRunModal — confirms cancellation of an active flow."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Static


class CancelRunModal(ModalScreen[bool]):
    """Confirm whether to cancel an active flow."""

    BINDINGS = [Binding("escape", "keep_running", "Keep running")]

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="cancel-run")
        dialog.border_title = "Cancel flow"
        with dialog:
            yield Static(
                "The active run will stop. Files already changed will not be reverted.\n"
                "Completed phases may be available when you resume the flow."
            )
            with Horizontal(classes="modal-actions"):
                yield Button("Keep running", id="btn-keep-running", variant="primary")
                yield Button("Cancel flow", id="btn-cancel-flow", variant="error")

    def on_mount(self) -> None:
        self.query_one("#btn-keep-running", Button).focus()

    def action_keep_running(self) -> None:
        """Dismiss the confirmation and continue the flow."""
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-keep-running":
            self.dismiss(False)
        elif event.button.id == "btn-cancel-flow":
            self.dismiss(True)
