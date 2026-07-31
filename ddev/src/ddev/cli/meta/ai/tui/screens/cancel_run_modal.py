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

    AUTO_FOCUS = "#btn-keep-running"
    BINDINGS = [Binding("escape", "keep_running", "Keep running")]

    def __init__(self, *, finalizing: bool = False) -> None:
        super().__init__()
        self._finalizing = finalizing

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="cancel-run")
        dialog.border_title = "Stop final summary" if self._finalizing else "Cancel flow"
        with dialog:
            if self._finalizing:
                yield Static(
                    "Phase execution is complete. Stop only the AI summary and finish with the deterministic result?"
                )
            else:
                yield Static(
                    "The active run will stop. Files already changed will not be reverted.\n"
                    "Completed phases may be available when you resume the flow."
                )
            with Horizontal(classes="modal-actions"):
                yield Button(
                    "Keep summarizing" if self._finalizing else "Keep running",
                    id="btn-keep-running",
                    variant="primary",
                )
                yield Button(
                    "Stop summary" if self._finalizing else "Cancel flow",
                    id="btn-cancel-flow",
                    variant="error",
                )

    def action_keep_running(self) -> None:
        """Dismiss the confirmation and continue the flow."""
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-keep-running":
            self.dismiss(False)
        elif event.button.id == "btn-cancel-flow":
            self.dismiss(True)
