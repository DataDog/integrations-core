# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for LaunchModal — typed input widgets, validation, and dismiss payload."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pytest
from textual import events
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, Input, Static, Switch

from ddev.ai.config.models import FlowInput, InputType


def object_flow_input(**overrides: object) -> FlowInput:
    data = {
        "name": "endpoint",
        "label": "Endpoint",
        "type": "object",
        "fields": [
            {"name": "url", "label": "URL", "type": "string"},
            {"name": "retries", "label": "Retries", "type": "number", "required": False},
            {"name": "enabled", "label": "Enabled", "type": "boolean"},
        ],
    }
    data.update(overrides)
    return FlowInput.model_validate(data)


def button_labeled(screen: Screen, label: str) -> Button:
    button = next((button for button in screen.query(Button) if str(button.label) == label), None)
    assert button is not None, f"Button labeled {label!r} was not visible"
    return button


# ---------------------------------------------------------------------------
# Widget rendering per InputType
# ---------------------------------------------------------------------------


async def test_launch_modal_occupies_at_least_half_viewport(make_launch_modal_app) -> None:
    viewport = (240, 100)
    app = make_launch_modal_app([])

    async with app.run_test(size=viewport) as pilot:
        await pilot.pause()
        dialog = app.screen.query_one("#dialog")
        actions = app.screen.query_one(".modal-actions")
        launch_button = app.screen.query_one("#btn-launch")

        assert dialog.region.width >= viewport[0] / 2
        assert dialog.region.height >= viewport[1] / 2
        assert actions.region.bottom == dialog.content_region.bottom
        assert launch_button.region.right == dialog.content_region.right


@pytest.mark.parametrize(
    "flow_input,widget_type,expected_value",
    [
        (FlowInput(name="s", label="S", input_type=InputType.STRING, default="hello"), Input, "hello"),
        (FlowInput(name="n", label="N", input_type=InputType.NUMBER, default=42), Input, "42"),
        (FlowInput(name="p", label="P", input_type=InputType.PATH, default="/tmp"), Input, "/tmp"),
    ],
)
async def test_textual_input_widgets_prefill_defaults(
    make_launch_modal_app, flow_input, widget_type, expected_value
) -> None:
    """String, number, and path inputs render as Textual Inputs with defaults."""
    app = make_launch_modal_app([flow_input])
    async with app.run_test() as pilot:
        await pilot.pause()
        modal = app.screen
        widget = modal.query_one(f"#input-{flow_input.name}", widget_type)
        assert widget.value == expected_value


async def test_number_input_has_number_validator(make_launch_modal_app) -> None:
    """number Input carries at least one validator."""
    app = make_launch_modal_app([FlowInput(name="n", label="N", input_type=InputType.NUMBER, default=7)])
    async with app.run_test() as pilot:
        await pilot.pause()
        modal = app.screen
        inp = modal.query_one("#input-n", Input)
        assert len(inp.validators) >= 1


@pytest.mark.parametrize("input_type", [InputType.STRING, InputType.NUMBER, InputType.PATH])
async def test_declared_input_placeholder_is_rendered_without_becoming_a_value(
    make_launch_modal_app, input_type: InputType
) -> None:
    """Custom placeholders remain visual hints and leave the input value empty."""
    flow_input = FlowInput(
        name="example",
        label="Example",
        input_type=input_type,
        placeholder="Example value",
        required=False,
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test() as pilot:
        await pilot.pause()
        widget = app.screen.query_one("#input-example", Input)

        assert widget.placeholder == "Example value"
        assert widget.value == ""


async def test_text_input_accepts_terminal_paste(make_launch_modal_app) -> None:
    """Bracketed terminal paste is inserted into the focused launch input."""
    app = make_launch_modal_app([FlowInput(name="s", label="S", input_type=InputType.STRING)])
    async with app.run_test() as pilot:
        await pilot.pause()
        inp = app.screen.query_one("#input-s", Input)
        inp.focus()
        inp.post_message(events.Paste("pasted value"))
        await pilot.pause()

        assert inp.value == "pasted value"


@pytest.mark.parametrize("default,expected", [(True, True), (False, False), ("true", True), ("false", False)])
async def test_boolean_switch_prefilled(make_launch_modal_app, default, expected) -> None:
    """boolean Switch state matches the default value."""
    app = make_launch_modal_app([FlowInput(name="b", label="B", input_type=InputType.BOOLEAN, default=default)])
    async with app.run_test() as pilot:
        await pilot.pause()
        modal = app.screen
        sw = modal.query_one("#input-b", Switch)
        assert sw.value is expected


async def test_object_input_prefills_and_submits_object_level_default(make_launch_modal_app, large_terminal) -> None:
    flow_input = object_flow_input(
        required=False,
        default={"url": "https://default.test", "enabled": True},
        fields=[
            {"name": "url", "label": "URL", "type": "string", "default": "https://child.test"},
            {"name": "retries", "label": "Retries", "type": "number", "required": False, "default": 3},
            {"name": "enabled", "label": "Enabled", "type": "boolean"},
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {
            "endpoint": {
                "url": "https://default.test",
                "retries": "3",
                "enabled": "true",
            },
            "prd": "Required product behavior.\n",
        }


async def test_object_null_parent_default_uses_child_default(make_launch_modal_app, large_terminal) -> None:
    flow_input = object_flow_input(
        required=False,
        default={"enabled": None},
        fields=[
            {"name": "enabled", "label": "Enabled", "type": "boolean", "required": False, "default": True},
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()

        assert app.screen.query_one("#input-endpoint-enabled", Switch).value is True

        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {
            "endpoint": {"enabled": "true"},
            "prd": "Required product behavior.\n",
        }


async def test_object_path_default_stays_raw_until_launch(make_launch_modal_app, large_terminal, tmp_path) -> None:
    source = tmp_path / "endpoint.txt"
    source.write_text("configuration-time content", encoding="utf-8")
    flow_input = object_flow_input(
        required=False,
        default={"source": source},
        fields=[
            {
                "name": "source",
                "label": "Source",
                "type": "path",
                "as_content": True,
            }
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()

        assert app.screen.query_one("#input-endpoint-source", Input).value == str(source)

        source.write_text("launch-time content", encoding="utf-8")
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {
            "endpoint": {"source": "launch-time content"},
            "prd": "Required product behavior.\n",
        }


# ---------------------------------------------------------------------------
# Cancel / escape closes modal with no result
# ---------------------------------------------------------------------------


async def test_cancel_button_dismisses_with_none(make_launch_modal_app, all_flow_inputs, large_terminal) -> None:
    """Pressing Cancel dismisses the modal without a value."""
    app = make_launch_modal_app(all_flow_inputs)
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-cancel")
        await pilot.pause()
        assert app.dismiss_result is None


async def test_escape_dismisses_with_none(make_launch_modal_app, all_flow_inputs) -> None:
    """Pressing Escape dismisses the modal without a value."""
    app = make_launch_modal_app(all_flow_inputs)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("#btn-cancel", Button).focus()
        await pilot.press("escape")
        await pilot.pause()
        assert app.dismiss_result is None


# ---------------------------------------------------------------------------
# Validation: invalid number blocks Launch
# ---------------------------------------------------------------------------


async def test_invalid_number_blocks_launch(make_launch_modal_app, large_terminal) -> None:
    """An unparseable number value prevents dismiss from being called."""
    app = make_launch_modal_app([FlowInput(name="n", label="N", input_type=InputType.NUMBER, default=1, required=True)])
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        inp = app.screen.query_one("#input-n", Input)
        await pilot.click(inp)
        # Clear and type invalid value
        for _ in range(10):
            await pilot.press("backspace")
        await pilot.press(*"notanumber")
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()
        assert app.dismiss_result == "NOT_SET"


async def test_non_finite_number_conversion_error_stays_inline(make_launch_modal_app, large_terminal) -> None:
    """Numbers accepted by float but rejected by ResolvedFlow remain in the modal."""
    app = make_launch_modal_app([FlowInput(name="n", label="N", input_type=InputType.NUMBER, default=1)])
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        app.screen.query_one("#input-n", Input).value = "NaN"
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == "NOT_SET"
        assert "must be a number" in str(app.screen.query_one("#launch-error", Static).render())


async def test_missing_as_content_path_error_stays_inline(make_launch_modal_app, tmp_path, large_terminal) -> None:
    """Unreadable content paths are reported without dismissing the modal."""
    missing = tmp_path / "missing.txt"
    app = make_launch_modal_app(
        [FlowInput(name="source", label="Source", input_type=InputType.PATH, default=str(missing), as_content=True)]
    )
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == "NOT_SET"
        assert "does not exist" in str(app.screen.query_one("#launch-error", Static).render())


# ---------------------------------------------------------------------------
# Validation: missing required field blocks Launch
# ---------------------------------------------------------------------------


async def test_missing_required_string_blocks_launch(make_launch_modal_app, large_terminal) -> None:
    """An empty required string field prevents dismiss from being called."""
    app = make_launch_modal_app(
        [FlowInput(name="s", label="S", input_type=InputType.STRING, default="", required=True)]
    )
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        # Ensure field is empty
        inp = app.screen.query_one("#input-s", Input)
        await pilot.click(inp)
        for _ in range(20):
            await pilot.press("backspace")
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()
        assert app.dismiss_result == "NOT_SET"


# ---------------------------------------------------------------------------
# Valid submission: dismiss with correct payload
# ---------------------------------------------------------------------------


async def test_valid_submission_dismisses_with_payload(make_launch_modal_app, large_terminal) -> None:
    """Valid inputs produce a dismiss payload matching runtime_variables output."""
    inputs = [
        FlowInput(name="s", label="S", input_type=InputType.STRING, default="world", required=True),
        FlowInput(name="b", label="B", input_type=InputType.BOOLEAN, default=False, required=False),
    ]
    app = make_launch_modal_app(inputs)
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()
        assert app.dismiss_result is not None
        assert app.dismiss_result != "NOT_SET"
        assert app.dismiss_result == {"s": "world", "b": "false", "prd": "Required product behavior.\n"}


async def test_valid_number_submission_dismisses(make_launch_modal_app, large_terminal) -> None:
    """A valid number value produces a dismissal."""
    app = make_launch_modal_app(
        [FlowInput(name="n", label="N", input_type=InputType.NUMBER, default=99, required=True)]
    )
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()
        assert app.dismiss_result is not None
        assert app.dismiss_result != "NOT_SET"
        assert app.dismiss_result == {"n": "99", "prd": "Required product behavior.\n"}


async def test_object_submission_dismisses_with_canonical_nested_payload(make_launch_modal_app, large_terminal) -> None:
    app = make_launch_modal_app([object_flow_input()])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        app.screen.query_one("#input-endpoint-url", Input).value = "https://example.test"
        app.screen.query_one("#input-endpoint-retries", Input).value = "2"
        app.screen.query_one("#input-endpoint-enabled", Switch).value = False
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {
            "endpoint": {
                "url": "https://example.test",
                "retries": "2",
                "enabled": "false",
            },
            "prd": "Required product behavior.\n",
        }


async def test_multi_scalar_entries_can_be_added_removed_and_submitted_in_order(
    make_launch_modal_app,
) -> None:
    flow_input = FlowInput(name="tags", label="Tags", input_type=InputType.STRING, multi=True, required=False)
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=(160, 100)) as pilot:
        await pilot.pause()
        add_button = button_labeled(app.screen, "+ Add Tag")
        add_button.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.focused, Input)
        await pilot.press(*"first")
        await pilot.press("tab")
        assert isinstance(app.focused, Button)
        assert str(app.focused.label) == "Remove"
        await pilot.press("tab")
        assert app.focused is add_button
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.focused, Input)
        await pilot.press(*"second")

        first_remove = button_labeled(app.screen, "Remove")
        first_remove.focus()
        await pilot.press("enter")
        await pilot.pause()
        button_labeled(app.screen, "Launch ▶").focus()
        await pilot.press("enter")
        await pilot.pause()

        assert app.dismiss_result == {"tags": ["second"], "prd": "Required product behavior.\n"}


async def test_singular_collection_label_adds_and_submits_value(make_launch_modal_app) -> None:
    flow_input = FlowInput(
        name="series",
        label="Series",
        input_type=InputType.STRING,
        multi=True,
        required=False,
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=(160, 100)) as pilot:
        await pilot.pause()
        add_button = button_labeled(app.screen, "+ Add Series")
        add_button.focus()
        await pilot.press("enter")
        await pilot.press(*"requests")
        button_labeled(app.screen, "Launch ▶").focus()
        await pilot.press("enter")
        await pilot.pause()

        assert app.dismiss_result == {"series": ["requests"], "prd": "Required product behavior.\n"}


async def test_required_multi_object_starts_with_a_usable_entry(make_launch_modal_app) -> None:
    flow_input = object_flow_input(
        name="endpoints",
        label="Endpoints",
        multi=True,
        fields=[
            {"name": "name", "label": "Name", "type": "string"},
            {"name": "url", "label": "URL", "type": "string"},
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=(160, 100)) as pilot:
        await pilot.pause()
        button_labeled(app.screen, "Remove").focus()
        await pilot.press("tab")
        await pilot.press(*"primary")
        await pilot.press("tab")
        await pilot.press(*"https://primary.test")
        button_labeled(app.screen, "Launch ▶").focus()
        await pilot.press("enter")
        await pilot.pause()

        assert app.dismiss_result == {
            "endpoints": [{"name": "primary", "url": "https://primary.test"}],
            "prd": "Required product behavior.\n",
        }


async def test_multi_object_entries_can_be_added_removed_and_submitted_in_order(
    make_launch_modal_app,
) -> None:
    flow_input = object_flow_input(
        name="endpoints",
        label="Endpoints",
        multi=True,
        required=False,
        fields=[
            {"name": "name", "label": "Name", "type": "string"},
            {"name": "url", "label": "URL", "type": "string"},
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=(160, 100)) as pilot:
        await pilot.pause()
        add_button = button_labeled(app.screen, "+ Add Endpoint")
        add_button.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.focused, Input)
        await pilot.press(*"first")
        await pilot.press("tab")
        assert isinstance(app.focused, Input)
        await pilot.press(*"https://first.test")

        add_button.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.focused, Input)
        await pilot.press(*"second")
        await pilot.press("tab")
        assert isinstance(app.focused, Input)
        await pilot.press(*"https://second.test")

        first_remove = button_labeled(app.screen, "Remove")
        first_remove.focus()
        await pilot.press("enter")
        await pilot.pause()
        button_labeled(app.screen, "Launch ▶").focus()
        await pilot.press("enter")
        await pilot.pause()

        assert app.dismiss_result == {
            "endpoints": [{"name": "second", "url": "https://second.test"}],
            "prd": "Required product behavior.\n",
        }


async def test_multi_defaults_launch_as_ordered_runtime_values(make_launch_modal_app, large_terminal) -> None:
    flow_input = FlowInput(
        name="ports",
        label="Ports",
        input_type=InputType.NUMBER,
        multi=True,
        required=False,
        default=[9090, 8080],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {"ports": ["9090", "8080"], "prd": "Required product behavior.\n"}


async def test_multi_defaults_are_restored_after_all_entries_are_removed(make_launch_modal_app, large_terminal) -> None:
    flow_input = FlowInput(
        name="ports",
        label="Ports",
        input_type=InputType.NUMBER,
        multi=True,
        required=False,
        default=[9090, 8080],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        for _ in range(2):
            button_labeled(app.screen, "Remove").focus()
            await pilot.press("enter")
            await pilot.pause()
        button_labeled(app.screen, "Launch ▶").focus()
        await pilot.press("enter")
        await pilot.pause()

        assert app.dismiss_result == {"ports": ["9090", "8080"], "prd": "Required product behavior.\n"}


async def test_required_multi_input_blocks_launch_while_initial_entry_is_empty(
    make_launch_modal_app, large_terminal
) -> None:
    app = make_launch_modal_app([FlowInput(name="tags", label="Tags", input_type=InputType.STRING, multi=True)])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == "NOT_SET"
        assert "cannot be empty" in str(app.screen.query_one("#launch-error", Static).render())


async def test_missing_required_object_field_stays_inline(make_launch_modal_app, large_terminal) -> None:
    app = make_launch_modal_app([object_flow_input()])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == "NOT_SET"
        assert "URL: required field cannot be empty" in str(app.screen.query_one("#launch-error", Static).render())


async def test_optional_object_with_every_child_empty_is_omitted(make_launch_modal_app, large_terminal) -> None:
    """An empty object means no parent value only when the parent itself is optional."""
    flow_input = object_flow_input(
        required=False,
        fields=[
            {"name": "url", "label": "URL", "type": "string"},
            {"name": "retries", "label": "Retries", "type": "number", "required": False},
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {"prd": "Required product behavior.\n"}


async def test_optional_object_with_any_child_value_validates_required_children(
    make_launch_modal_app, large_terminal
) -> None:
    """Once an optional object has content, it is present and required child rules apply."""
    flow_input = object_flow_input(
        required=False,
        fields=[
            {"name": "url", "label": "URL", "type": "string"},
            {"name": "retries", "label": "Retries", "type": "number", "required": False},
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        app.screen.query_one("#input-endpoint-retries", Input).value = "2"
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == "NOT_SET"
        assert "URL: required field cannot be empty" in str(app.screen.query_one("#launch-error", Static).render())


async def test_optional_object_with_boolean_field_is_present(make_launch_modal_app, large_terminal) -> None:
    """Boolean switches always supply true or false, matching top-level boolean inputs."""
    flow_input = object_flow_input(
        required=False,
        fields=[
            {
                "name": "enabled",
                "label": "Enabled",
                "type": "boolean",
                "required": False,
            }
        ],
    )
    app = make_launch_modal_app([flow_input])

    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        assert app.screen.query_one("#input-endpoint-enabled", Switch).value is False

        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {
            "endpoint": {"enabled": "false"},
            "prd": "Required product behavior.\n",
        }


@pytest.mark.parametrize(
    "flow_input",
    [
        FlowInput(name="s", label="S", input_type=InputType.STRING, default=None, required=False),
        FlowInput(name="n", label="N", input_type=InputType.NUMBER, default=None, required=False),
        FlowInput(
            name="p",
            label="P",
            input_type=InputType.PATH,
            default=None,
            required=False,
            as_content=True,
        ),
    ],
    ids=["string", "number", "path-as-content"],
)
async def test_optional_empty_field_is_omitted(make_launch_modal_app, large_terminal, flow_input: FlowInput) -> None:
    """An empty optional field is omitted from the launch payload."""
    app = make_launch_modal_app([flow_input])
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert app.dismiss_result == {"prd": "Required product behavior.\n"}


# ---------------------------------------------------------------------------
# Modal structure
# ---------------------------------------------------------------------------


async def test_launch_modal_has_dialog_launch_id(make_launch_modal_app, all_flow_inputs) -> None:
    """LaunchModal contains a #dialog element with .launch class."""
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    app = make_launch_modal_app(all_flow_inputs)
    async with app.run_test() as pilot:
        await pilot.pause()
        modal = app.screen
        assert isinstance(modal, LaunchModal)
        dialog = modal.query_one("#dialog")
        assert "launch" in dialog.classes


async def test_launch_modal_has_scrollable_fields_region(make_launch_modal_app, all_flow_inputs) -> None:
    """LaunchModal groups inputs in a dedicated scrollable fields region."""
    app = make_launch_modal_app(all_flow_inputs)
    async with app.run_test() as pilot:
        await pilot.pause()
        fields = app.screen.query_one("#launch-fields")
        assert fields.query_one("#input-my_string", Input)
        assert fields.query_one("#input-my_bool", Switch)


async def test_launch_modal_actions_are_horizontal(make_launch_modal_app, all_flow_inputs) -> None:
    """LaunchModal renders its actions in one row without coupling to button order."""
    app = make_launch_modal_app(all_flow_inputs)
    async with app.run_test() as pilot:
        await pilot.pause()
        actions = app.screen.query_one(".modal-actions", Horizontal)
        button_ids = [button.id for button in actions.query(Button)]
        assert set(button_ids) == {"btn-cancel", "btn-launch"}
        assert app.screen.query_one("#btn-launch", Button).variant == "primary"


async def test_launch_modal_is_modal_screen() -> None:
    """LaunchModal extends ModalScreen."""
    from textual.screen import ModalScreen

    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    assert issubclass(LaunchModal, ModalScreen)


# ---------------------------------------------------------------------------
# Missing edge case: required path field blocks launch
# ---------------------------------------------------------------------------


async def test_missing_required_path_blocks_launch(make_launch_modal_app, large_terminal) -> None:
    """An empty required path field prevents dismiss from being called."""
    app = make_launch_modal_app(
        [FlowInput(name="p", label="P", input_type=InputType.PATH, default=None, required=True)]
    )
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        # Ensure the path field is empty (no default)
        inp = app.screen.query_one("#input-p", Input)
        assert inp.value == ""
        await pilot.click("#btn-launch")
        await pilot.pause()
        assert app.dismiss_result == "NOT_SET"


# ---------------------------------------------------------------------------
# Path autocomplete: home-dir expansion, no forced completion on Enter
# ---------------------------------------------------------------------------


async def test_path_autocomplete_expands_home_directory(make_launch_modal_app, large_terminal) -> None:
    """A leading ``~`` is expanded to the home directory when listing candidates."""
    from textual_autocomplete import TargetState

    app = make_launch_modal_app(
        [FlowInput(name="p", label="P", input_type=InputType.PATH, default=None, required=False)]
    )
    async with app.run_test(size=large_terminal):
        from ddev.cli.meta.ai.tui.widgets.launch_flow_input import TogoPathAutoComplete

        autocomplete = app.screen.query_one(TogoPathAutoComplete)
        home_candidates = autocomplete.get_candidates(
            TargetState(text=str(Path.home()) + "/", cursor_position=len(str(Path.home())) + 1)
        )
        tilde_candidates = autocomplete.get_candidates(TargetState(text="~/", cursor_position=2))
        assert {c.main for c in tilde_candidates} == {c.main for c in home_candidates}


async def test_path_autocomplete_renders_all_directory_suggestions(
    make_launch_modal_app, large_terminal, tmp_path
) -> None:
    """Path suggestions remain visible when another launch input follows."""
    candidate_names = [f"autocomplete-{letter}-unique" for letter in "abcdefgh"]
    for candidate_name in candidate_names:
        (tmp_path / candidate_name).mkdir()

    app = make_launch_modal_app(
        [
            FlowInput(name="path", label="Path", input_type=InputType.PATH, default=str(tmp_path)),
            FlowInput(name="following", label="Following", input_type=InputType.NUMBER),
        ]
    )
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        path_input = app.screen.query_one("#input-path", Input)
        await pilot.click(path_input)
        await pilot.press("end", "/")
        await pilot.pause()

        screenshot = ElementTree.fromstring(app.export_screenshot())
        rendered_text = "".join(element.text or "" for element in screenshot.iter("{http://www.w3.org/2000/svg}text"))
        assert candidate_names[-1] in rendered_text


async def test_path_autocomplete_does_not_force_completion_on_enter(
    make_launch_modal_app, large_terminal, tmp_path, monkeypatch
) -> None:
    """Enter keeps the field's literal text even when the dropdown has a matching suggestion."""
    (tmp_path / "sandbox").mkdir()
    monkeypatch.chdir(tmp_path)
    app = make_launch_modal_app(
        [FlowInput(name="p", label="P", input_type=InputType.PATH, default=None, required=False)]
    )
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        inp = app.screen.query_one("#input-p", Input)
        await pilot.click(inp)
        await pilot.press(*"sand")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert inp.value == "sand"


async def test_path_autocomplete_keeps_text_on_escape_with_no_candidates(make_launch_modal_app, large_terminal) -> None:
    """Escape must not fall through to the modal's cancel binding while the path field has focus."""
    app = make_launch_modal_app(
        [FlowInput(name="p", label="P", input_type=InputType.PATH, default=None, required=False)]
    )
    async with app.run_test(size=large_terminal) as pilot:
        await pilot.pause()
        inp = app.screen.query_one("#input-p", Input)
        await pilot.click(inp)
        await pilot.press(*"nonexistent-output-dir")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.dismiss_result == "NOT_SET"
        assert inp.value == "nonexistent-output-dir"
