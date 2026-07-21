# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""LaunchModal — collects typed flow inputs and dismisses with a validated payload."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Static

from ddev.ai.config.models import ResolvedFlow
from ddev.cli.meta.ai.tui.widgets.launch_flow_input import LaunchFlowInput

type LaunchInputValues = dict[str, str]


class LaunchModal(ModalScreen):
    """Collect and convert a flow's typed runtime inputs."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, flow: ResolvedFlow) -> None:
        super().__init__()
        self.flow = flow
        self.launch_inputs = [LaunchFlowInput.get(flow_input) for flow_input in flow.inputs]

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="launch")
        dialog.border_title = f"launch · {self.flow.name or 'flow'}"
        with dialog:
            yield Static("Provide inputs for this run, then start.", classes="desc")
            with Widget(id="launch-fields"):
                yield from self.launch_inputs
            yield Static("", id="launch-error")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Launch ▶", id="btn-launch", variant="primary")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_cancel(self) -> None:
        self.dismiss(None)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-launch":
            self._try_launch()

    # ------------------------------------------------------------------
    # Validation + dismiss
    # ------------------------------------------------------------------

    def _try_launch(self) -> None:
        values: dict[str, object] = {}
        for launch_input in self.launch_inputs:
            try:
                value = launch_input.get_value()
            except ValueError as error:
                self._show_error(str(error))
                return
            if value is None:
                continue
            values[launch_input.flow_input.name] = value
        try:
            converted = self.flow.convert_inputs(values)
        except ValueError as error:
            self._show_error(str(error))
            return
        self.dismiss(converted)

    def _show_error(self, message: str) -> None:
        try:
            err = self.query_one("#launch-error", Static)
            err.update(f"[red]{message}[/red]")
        except Exception:
            pass
