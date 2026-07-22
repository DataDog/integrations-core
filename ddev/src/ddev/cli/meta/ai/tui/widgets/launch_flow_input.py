# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Composable launch input widgets."""

from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.content import Content
from textual.css.query import NoMatches
from textual.geometry import Size
from textual.validation import Number
from textual.widget import Widget
from textual.widgets import Button, Input, Static, Switch
from textual_autocomplete import DropdownItem, PathAutoComplete, TargetState

from ddev.ai.config.models import FlowInput, FlowInputField, InputType


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


def spec_for_field(flow_input: FlowInput, field: FlowInputField) -> EditorSpec:
    """Adapt an object field to its UI editor specification."""
    return _spec_for_object_field(spec_for_input(flow_input), field)


def _spec_for_object_field(object_spec: EditorSpec, field: FlowInputField) -> EditorSpec:
    object_default = object_spec.default if isinstance(object_spec.default, Mapping) else {}
    parent_default = object_default.get(field.name)
    return EditorSpec(
        widget_id=f"{object_spec.widget_id}-{field.name}",
        value_name=field.name,
        input_type=field.input_type,
        label=field.label,
        required=field.required,
        default=field.default if parent_default is None else parent_default,
        placeholder=field.placeholder,
    )


def spec_for_item(flow_input: FlowInput, index: int) -> EditorSpec:
    """Adapt one multi input item to its UI editor specification."""
    defaults = flow_input.default if isinstance(flow_input.default, list) else []
    default = defaults[index] if index < len(defaults) else None
    return EditorSpec(
        widget_id=f"input-{flow_input.name}-item-{index}",
        value_name=flow_input.name,
        input_type=flow_input.input_type,
        label=flow_input.label,
        required=flow_input.required,
        default=default,
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


def get_scalar_value_editor(spec: EditorSpec) -> LaunchValueEditor[str] | LaunchValueEditor[bool]:
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


class ObjectValueEditor(LaunchValueEditor[dict[str, str | bool]]):
    """Edit the scalar fields declared by an object input."""

    def __init__(self, spec: EditorSpec, field_specs: tuple[EditorSpec, ...]) -> None:
        super().__init__(spec)
        self.field_specs = field_specs
        self.editors = {field.value_name: get_scalar_value_editor(field) for field in field_specs}

    def compose(self) -> ComposeResult:
        for field in self.field_specs:
            with Vertical(classes="object-field"):
                yield Static(f"{field.label} ({field.input_type.value})", classes="object-field-label")
                yield self.editors[field.value_name]

    def get_value(self) -> dict[str, str | bool] | None:
        field_values = {field.value_name: self.editors[field.value_name].get_value() for field in self.field_specs}
        if (
            not self.spec.required
            and self.spec.default is None
            and all(value is None for value in field_values.values())
        ):
            return None

        values: dict[str, str | bool] = {}
        for field in self.field_specs:
            value = field_values[field.value_name]
            if value is None:
                if field.required:
                    raise ValueError(f"{field.label}: required field cannot be empty.")
                continue
            values[field.value_name] = value
        return values


def get_value_editor(
    flow_input: FlowInput,
) -> LaunchValueEditor[str] | LaunchValueEditor[bool] | LaunchValueEditor[dict[str, str | bool]]:
    """Create the editor declared by a flow input."""
    spec = spec_for_input(flow_input)
    if flow_input.input_type is InputType.OBJECT:
        return ObjectValueEditor(spec, tuple(spec_for_field(flow_input, field) for field in flow_input.fields))
    return get_scalar_value_editor(spec)


class LaunchFlowInput[T](Widget, ABC, metaclass=WidgetABCMeta):
    """Common framed interface for one declared launch input."""

    def __init__(self, flow_input: FlowInput) -> None:
        super().__init__(classes="launch-flow-input")
        self.flow_input = flow_input
        self.border_title = f"{flow_input.label.upper()} ({flow_input.input_type.value})"

    @classmethod
    def get(
        cls,
        flow_input: FlowInput,
    ) -> (
        LaunchFlowInput[str]
        | LaunchFlowInput[bool]
        | LaunchFlowInput[dict[str, str | bool]]
        | LaunchFlowInput[list[str]]
        | LaunchFlowInput[list[bool]]
        | LaunchFlowInput[list[dict[str, str | bool]]]
    ):
        """Create the launch widget declared by a flow input."""
        if flow_input.multi:
            return MultiLaunchFlowInput(flow_input)
        return SingleLaunchFlowInput(flow_input, get_value_editor(flow_input))

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


type LaunchEditor = LaunchValueEditor[str] | LaunchValueEditor[bool] | LaunchValueEditor[dict[str, str | bool]]


class MultiValueEntry(Widget):
    """Display one removable value in a repeated launch input."""

    def __init__(self, editor: LaunchEditor, *, object_entry: bool, item_label: str, ordinal: int) -> None:
        classes = "multi-entry object-entry" if object_entry else "multi-entry scalar-entry"
        super().__init__(classes=classes)
        self.editor = editor
        self.object_entry = object_entry
        self.item_label = item_label
        self.ordinal = ordinal

    def compose(self) -> ComposeResult:
        if self.object_entry:
            with Horizontal(classes="multi-entry-header"):
                yield Static(f"{self.item_label} {self.ordinal}", classes="multi-entry-title")
                yield Button("Remove", classes="remove-multi-item", variant="warning")
            yield self.editor
        else:
            with Horizontal(classes="multi-scalar-row"):
                yield self.editor
                yield Button("Remove", classes="remove-multi-item", variant="warning")

    def set_ordinal(self, ordinal: int) -> None:
        self.ordinal = ordinal
        if self.object_entry and self.is_mounted:
            self.query_one(".multi-entry-title", Static).update(f"{self.item_label} {ordinal}")


class MultiLaunchFlowInput(LaunchFlowInput[list[object]]):
    """Collect an ordered list using repeated single-value editors."""

    def __init__(self, flow_input: FlowInput) -> None:
        super().__init__(flow_input)
        self.border_title = f"{flow_input.label.upper()} (multi · {flow_input.input_type.value})"
        self.next_entry_id = 0
        defaults = flow_input.default if isinstance(flow_input.default, list) else []
        self.entries: list[MultiValueEntry] = []
        initial_entry_count = len(defaults) if defaults else int(flow_input.required)
        for _ in range(initial_entry_count):
            self.entries.append(self._create_entry())

    def compose(self) -> ComposeResult:
        with Vertical(classes="multi-items"):
            yield from self.entries
        yield Button(f"+ Add {self._item_label()}", classes="add-multi-item")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class("add-multi-item"):
            entry = self._create_entry()
            self.entries.append(entry)
            await self.query_one(".multi-items", Vertical).mount(entry)
            self._renumber_entries()
            controls = entry.query("Input, Switch")
            if controls:
                controls.first().focus()
            event.stop()
        elif event.button.has_class("remove-multi-item"):
            entry = next(
                ancestor for ancestor in event.button.ancestors_with_self if isinstance(ancestor, MultiValueEntry)
            )
            self.entries.remove(entry)
            await entry.remove()
            self._renumber_entries()
            event.stop()

    def get_value(self) -> list[object]:
        values: list[object] = []
        for index, entry in enumerate(self.entries, start=1):
            value = entry.editor.get_value()
            if value is None:
                raise ValueError(f"{self.flow_input.label} item {index}: cannot be empty.")
            values.append(value)
        if not values and self.flow_input.required:
            raise ValueError(f"{self.flow_input.label}: must contain at least one item.")
        return values

    def _create_entry(self) -> MultiValueEntry:
        entry_id = self.next_entry_id
        self.next_entry_id += 1
        item_spec = spec_for_item(self.flow_input, entry_id)
        if self.flow_input.input_type is InputType.OBJECT:
            field_specs = tuple(_spec_for_object_field(item_spec, field) for field in self.flow_input.fields)
            editor: LaunchEditor = ObjectValueEditor(item_spec, field_specs)
        else:
            editor = get_scalar_value_editor(item_spec)
        return MultiValueEntry(
            editor,
            object_entry=self.flow_input.input_type is InputType.OBJECT,
            item_label=self._item_label(),
            ordinal=len(self.entries) + 1,
        )

    def _renumber_entries(self) -> None:
        for ordinal, entry in enumerate(self.entries, start=1):
            entry.set_ordinal(ordinal)

    def _item_label(self) -> str:
        label = self.flow_input.label
        lowercase_label = label.lower()
        if lowercase_label.endswith(("ss", "us", "is", "series")):
            return label
        if lowercase_label.endswith("ies"):
            return f"{label[:-3]}y"
        if lowercase_label.endswith("s"):
            return label[:-1]
        return label
