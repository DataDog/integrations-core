# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Composable launch input widgets."""

from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from textual import events
from textual.app import ComposeResult
from textual.content import Content
from textual.css.query import NoMatches
from textual.geometry import Size
from textual.validation import Number
from textual.widget import Widget
from textual.widgets import Input, Switch
from textual_autocomplete import DropdownItem, PathAutoComplete, TargetState

from ddev.ai.config.models import FlowInput, InputType


@dataclass(frozen=True)
class EditorSpec:
    """Describe one value edited by a launch input control."""

    widget_id: str
    value_name: str
    input_type: InputType
    label: str
    required: bool
    default: object | None
    placeholder: str | None


def spec_for_input(flow_input: FlowInput) -> EditorSpec:
    """Adapt a flow input to its UI editor specification."""
    return EditorSpec(
        widget_id=f"input-{flow_input.name}",
        value_name=flow_input.name,
        input_type=flow_input.input_type,
        label=flow_input.label,
        required=flow_input.required,
        default=flow_input.default,
        placeholder=flow_input.placeholder,
    )


class WidgetABCMeta(type(Widget), ABCMeta):  # type: ignore[misc]
    """Combine Textual's widget metaclass with abstract interfaces."""


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

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        try:
            option_count = self.option_list.option_count
        except NoMatches:
            return super().get_content_height(container, viewport, width)
        return min(option_count, 12)

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


class LaunchValueEditor[T](Widget, ABC, metaclass=WidgetABCMeta):
    """Edit one raw launch value."""

    def __init__(self, spec: EditorSpec) -> None:
        super().__init__(classes="launch-value-editor")
        self.spec = spec

    @abstractmethod
    def get_value(self) -> T | None:
        """Return the raw value represented by this editor."""


class TextLaunchValueEditor(LaunchValueEditor[str], ABC):
    """Base editor for text-like launch values."""

    def _input(self) -> Input:
        return self.query_one(f"#{self.spec.widget_id}", Input)

    def _get_text(self) -> str | None:
        return self._input().value.strip() or None

    def _make_input(self, *, validators: list[Number] | None = None) -> Input:
        default = str(self.spec.default) if self.spec.default is not None else ""
        return Input(
            value=default,
            placeholder=self.spec.placeholder or "",
            id=self.spec.widget_id,
            validators=validators,
        )


class StringLaunchValueEditor(TextLaunchValueEditor):
    """Edit a string launch value."""

    def compose(self) -> ComposeResult:
        yield self._make_input()

    def get_value(self) -> str | None:
        return self._get_text()


class NumberLaunchValueEditor(TextLaunchValueEditor):
    """Edit a numeric launch value."""

    def compose(self) -> ComposeResult:
        yield self._make_input(validators=[Number()])

    def get_value(self) -> str | None:
        value = self._get_text()
        if value is None:
            return None
        try:
            float(value)
        except ValueError:
            raise ValueError(f"{self.spec.label}: must be a valid number.") from None
        return value


class BooleanLaunchValueEditor(LaunchValueEditor[bool]):
    """Edit a boolean launch value."""

    def compose(self) -> ComposeResult:
        default = self.spec.default
        enabled = default if isinstance(default, bool) else str(default).lower() == "true"
        yield Switch(value=enabled, id=self.spec.widget_id)

    def get_value(self) -> bool:
        return self.query_one(f"#{self.spec.widget_id}", Switch).value


class PathLaunchValueEditor(TextLaunchValueEditor):
    """Edit a path launch value with autocomplete."""

    def compose(self) -> ComposeResult:
        yield self._make_input()
        yield TogoPathAutoComplete(target=f"#{self.spec.widget_id}")

    def get_value(self) -> str | None:
        return self._get_text()


def get_value_editor(spec: EditorSpec) -> LaunchValueEditor[str] | LaunchValueEditor[bool]:
    """Create the scalar editor declared by an editor specification."""
    match spec.input_type:
        case InputType.STRING:
            return StringLaunchValueEditor(spec)
        case InputType.NUMBER:
            return NumberLaunchValueEditor(spec)
        case InputType.BOOLEAN:
            return BooleanLaunchValueEditor(spec)
        case InputType.PATH:
            return PathLaunchValueEditor(spec)
        case unexpected:
            assert_never(unexpected)


class LaunchFlowInput[T](Widget, ABC, metaclass=WidgetABCMeta):
    """Common framed interface for one declared launch input."""

    def __init__(self, flow_input: FlowInput) -> None:
        super().__init__(classes="launch-flow-input")
        self.flow_input = flow_input
        self.border_title = f"{flow_input.label.upper()} ({flow_input.input_type.value})"

    @classmethod
    def get(cls, flow_input: FlowInput) -> LaunchFlowInput[str] | LaunchFlowInput[bool]:
        """Create the launch widget declared by a flow input."""
        return SingleLaunchFlowInput(flow_input, get_value_editor(spec_for_input(flow_input)))

    @abstractmethod
    def get_value(self) -> T | None:
        """Return the validated raw input value."""


class SingleLaunchFlowInput[T](LaunchFlowInput[T]):
    """Frame one scalar value editor."""

    def __init__(self, flow_input: FlowInput, editor: LaunchValueEditor[T]) -> None:
        super().__init__(flow_input)
        self.editor = editor

    def compose(self) -> ComposeResult:
        yield self.editor

    def get_value(self) -> T | None:
        value = self.editor.get_value()
        if value is None and self.flow_input.required:
            raise ValueError(f"{self.flow_input.label}: required field cannot be empty.")
        return value
