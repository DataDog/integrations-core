# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""LaunchModal — collects typed flow inputs and dismisses with a validated payload."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.content import Content
from textual.screen import ModalScreen
from textual.validation import Number
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static, Switch
from textual_autocomplete import DropdownItem, PathAutoComplete, TargetState

from ddev.ai.config.models import FlowInput, InputType, ResolvedFlow

type LaunchInputValue = str | bool
type LaunchInputValues = dict[str, str]


class TogoPathAutoComplete(PathAutoComplete):
    """PathAutoComplete that expands a leading ``~`` and skips emoji prefixes.

    The typed value is never rewritten to an existing entry: Enter always
    submits the field's literal text (including paths that don't exist yet,
    e.g. an output directory to be created), and only Tab accepts a
    suggestion from the dropdown.
    """

    def __init__(self, target: Input | str) -> None:
        super().__init__(
            target,
            folder_prefix=Content(""),
            file_prefix=Content(""),
        )

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        current_input = target_state.text[: target_state.cursor_position]
        if current_input.startswith("~"):
            expanded = str(Path(current_input).expanduser())
            if current_input.endswith("/") and not expanded.endswith("/"):
                expanded += "/"
            target_state = TargetState(text=expanded, cursor_position=len(expanded))
        return super().get_candidates(target_state)

    def _listen_to_messages(self, event: events.Event) -> None:
        """Handle enter/escape ourselves instead of delegating to the base class.

        The base implementation only runs its enter/escape handling when the dropdown
        currently has at least one candidate (``option_list.option_count`` — it auto-hides
        with zero matches), and even then it applies the highlighted completion on enter
        regardless of ``prevent_default_enter``. Neither behavior is what we want for a
        path field that must accept freely typed, possibly nonexistent paths: typing a new
        output directory (no matching candidates) left enter/escape unhandled by the
        dropdown entirely, so escape fell through to the modal's own ``escape`` binding and
        dismissed the whole dialog, discarding whatever was typed. We handle both keys
        directly based on whether the path field itself has focus (not on the dropdown's
        visibility, which can't be relied on), so the typed text is never silently
        overwritten or discarded.
        """
        if isinstance(event, events.Key) and self.target.has_focus:
            if event.key == "enter":
                if self.display:
                    self.action_hide()
                return
            if event.key == "escape":
                event.prevent_default()
                event.stop()
                if self.display:
                    self.action_hide()
                return
        super()._listen_to_messages(event)


class LaunchModal(ModalScreen):
    """Collect and convert a flow's typed runtime inputs."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, flow: ResolvedFlow) -> None:
        super().__init__()
        self.flow = flow

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        dialog = Widget(id="dialog", classes="launch")
        dialog.border_title = f"launch · {self.flow.name or 'flow'}"
        with dialog:
            yield Static("Provide inputs for this run, then start.", classes="desc")
            with Widget(id="launch-fields"):
                yield from self._compose_inputs()
            yield Static("", id="launch-error")
            with Horizontal(classes="modal-actions"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Launch ▶", id="btn-launch", variant="primary")

    def _compose_inputs(self) -> Iterator[Widget]:
        for inp in self.flow.inputs:
            yield Label(f"{inp.label.upper()} ({inp.input_type.value})", classes="eyebrow")
            yield from self._widget_for(inp)

    def _widget_for(self, inp: FlowInput) -> Iterator[Widget]:
        widget_id = f"input-{inp.name}"
        if inp.input_type == InputType.BOOLEAN:
            default_enabled = inp.default if isinstance(inp.default, bool) else str(inp.default).lower() == "true"
            yield Switch(value=default_enabled, id=widget_id)
        elif inp.input_type == InputType.NUMBER:
            default_text = str(inp.default) if inp.default is not None else ""
            yield Input(value=default_text, placeholder=inp.placeholder or "", id=widget_id, validators=[Number()])
        elif inp.input_type == InputType.PATH:
            default_text = str(inp.default) if inp.default is not None else ""
            path_input = Input(value=default_text, placeholder=inp.placeholder or "", id=widget_id)
            yield path_input
            yield TogoPathAutoComplete(target=f"#{widget_id}")
        else:
            # STRING (default)
            default_text = str(inp.default) if inp.default is not None else ""
            yield Input(value=default_text, placeholder=inp.placeholder or "", id=widget_id)

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
        values: dict[str, LaunchInputValue] = {}
        for inp in self.flow.inputs:
            widget_id = f"input-{inp.name}"
            ok, value = self._read_value(inp, widget_id)
            if not ok:
                return
            if value is None:
                continue
            values[inp.name] = value
        try:
            converted = self.flow.convert_inputs(values)
        except ValueError as error:
            self._show_error(str(error))
            return
        self.dismiss(converted)

    def _read_value(
        self, inp: FlowInput, widget_id: str
    ) -> tuple[Literal[True], LaunchInputValue | None] | tuple[Literal[False], None]:
        """Read and validate the value for one input.

        Returns (success, value); on failure shows an inline error.
        """
        if inp.input_type == InputType.BOOLEAN:
            sw = self.query_one(f"#{widget_id}", Switch)
            return True, sw.value

        widget = self.query_one(f"#{widget_id}", Input)
        text = widget.value.strip()

        if inp.required and not text:
            self._show_error(f"{inp.label}: required field cannot be empty.")
            return False, None
        if not text:
            return True, None

        if inp.input_type == InputType.NUMBER:
            try:
                float(text)
            except ValueError:
                self._show_error(f"{inp.label}: must be a valid number.")
                return False, None

        return True, text

    def _show_error(self, message: str) -> None:
        try:
            err = self.query_one("#launch-error", Static)
            err.update(f"[red]{message}[/red]")
        except Exception:
            pass
