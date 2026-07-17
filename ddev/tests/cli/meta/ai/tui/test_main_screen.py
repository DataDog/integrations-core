# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for MainScreen and FlowCard engine results, layout, and interactions."""

from __future__ import annotations

from pathlib import Path

from ddev.ai.config.errors import ErrorKind, FlowError
from ddev.ai.config.models import ConfigStatus, FlowResult

# ---------------------------------------------------------------------------
# TogoApp: screen stack after mount
# ---------------------------------------------------------------------------


async def test_app_screen_stack_has_two_screens_after_mount(make_flow, make_togo_app):
    """After mount, screen_stack has the default screen + MainScreen."""
    app = make_togo_app([make_flow("Alpha Flow", n_phases=3), make_flow("Beta Flow", n_phases=1)])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert len(app.screen_stack) == 2


# ---------------------------------------------------------------------------
# FlowCard widget
# ---------------------------------------------------------------------------


async def test_main_screen_renders_provider_flows(make_flow, make_togo_app):
    """MainScreen renders one FlowCard per provider flow with the expected metadata."""
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    app = make_togo_app([make_flow("Alpha Flow", n_phases=3), make_flow("Beta Flow", n_phases=1)])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        cards = list(pilot.app.screen.query(FlowCard))
        assert len(cards) == 2
        names = [c.flow.name for c in cards]
        assert names == ["Alpha Flow", "Beta Flow"]
        phase_counts = {c.flow.name: c.phase_count for c in cards}
        assert phase_counts["Alpha Flow"] == 3
        assert phase_counts["Beta Flow"] == 1


async def test_main_screen_sorts_valid_and_broken_results(make_flow, make_togo_app):
    broken = FlowResult(
        "Alpha Broken",
        ConfigStatus.BROKEN,
        [FlowError(ErrorKind.AGENT, "provider unavailable", subject="writer")],
    )
    valid = make_flow("Zulu Valid", n_phases=1)
    app = make_togo_app([valid], results=[FlowResult(valid.name, ConfigStatus.OK, resolved=valid), broken])

    async with app.run_test() as pilot:
        await pilot.pause()
        cards = list(app.screen.query("FlowCard"))

    assert [card.result.name for card in cards] == ["Alpha Broken", "Zulu Valid"]
    assert "broken" in cards[0].classes
    assert "valid" in cards[1].classes


async def test_broken_flow_keyboard_opens_grouped_diagnostics(make_flow, make_togo_app):
    broken = FlowResult(
        "Broken Flow",
        ConfigStatus.BROKEN,
        [
            FlowError(
                ErrorKind.AGENT,
                "provider unavailable",
                subject="writer",
                phase="review",
                sources=[Path("/tmp/agent.yaml")],
            ),
            FlowError(ErrorKind.PROMPT, "prompt missing", phase="review"),
        ],
    )
    app = make_togo_app([], results=[broken])

    async with app.run_test() as pilot:
        await pilot.pause()
        card = app.screen.query_one("FlowCard")
        card.focus()
        await pilot.press("enter")
        await pilot.pause()

        from ddev.cli.meta.ai.tui.screens.diagnostics_modal import FlowDiagnosticsModal

        assert isinstance(app.screen, FlowDiagnosticsModal)
        assert len(app.screen.query(".diagnostic-error")) == 2
        rendered = " ".join(str(widget.render()) for widget in app.screen.query("Static"))
        assert "provider unavailable" in rendered
        assert "writer" in rendered
        assert "review" in rendered
        assert str(Path("/tmp/agent.yaml")) in rendered
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.__class__.__name__ == "MainScreen"


async def test_diagnostics_display_complete_error_report(make_togo_app):
    validation_message = (
        "Input should be a valid string "
        "[type=string_type, input_value={'name': 'integration', 'type': 'string'}, input_type=dict]"
    )
    broken = FlowResult(
        "Broken Flow",
        ConfigStatus.BROKEN,
        [
            FlowError(
                ErrorKind.FLOW,
                validation_message,
                subject="inputs",
                sources=[Path("/tmp/flow.yaml")],
            ),
            FlowError(ErrorKind.PROMPT, "Referenced prompt was not found", phase="generate"),
        ],
    )
    app = make_togo_app([], results=[broken])

    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("FlowCard").on_click()
        await pilot.pause()

        rendered = " ".join(str(widget.render()) for widget in app.screen.query(".diagnostic-error"))
        assert "01 · flow" in rendered
        assert validation_message in rendered
        assert "subject: inputs" in rendered
        assert str(Path("/tmp/flow.yaml")) in rendered
        assert "02 · prompt" in rendered
        assert "Referenced prompt was not found" in rendered
        assert "phase: generate" in rendered


async def test_diagnostics_modal_occupies_at_least_half_viewport(make_togo_app):
    viewport = (240, 100)
    broken = FlowResult(
        "Broken Flow",
        ConfigStatus.BROKEN,
        [FlowError(ErrorKind.FLOW, "Invalid flow")],
    )
    app = make_togo_app([], results=[broken])

    async with app.run_test(size=viewport) as pilot:
        await pilot.pause()
        app.screen.query_one("FlowCard").on_click()
        await pilot.pause()
        dialog = app.screen.query_one("#dialog")
        actions = app.screen.query_one(".modal-actions")
        close_button = app.screen.query_one("#btn-close")

        assert dialog.region.width >= viewport[0] / 2
        assert dialog.region.height >= viewport[1] / 2
        assert actions.region.bottom == dialog.content_region.bottom
        assert close_button.region.right == dialog.content_region.right


async def test_broken_flow_click_opens_diagnostics(make_togo_app):
    broken = FlowResult(
        "Broken Flow",
        ConfigStatus.BROKEN,
        [FlowError(ErrorKind.FLOW, "invalid flow")],
    )
    app = make_togo_app([], results=[broken])

    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen.query_one("FlowCard").on_click()
        await pilot.pause()

        assert app.screen.__class__.__name__ == "FlowDiagnosticsModal"


async def test_broken_flow_drag_selection_does_not_open_diagnostics(monkeypatch, make_togo_app):
    broken = FlowResult(
        "Broken Flow",
        ConfigStatus.BROKEN,
        [FlowError(ErrorKind.FLOW, "invalid flow")],
    )
    app = make_togo_app([], results=[broken])

    async with app.run_test() as pilot:
        await pilot.pause()
        monkeypatch.setattr(app.screen, "get_selected_text", lambda: "selected diagnostics")
        app.screen.query_one("FlowCard").on_click()
        await pilot.pause()

        assert app.screen.__class__.__name__ == "MainScreen"


async def test_flow_card_is_focusable(make_flow):
    """FlowCard is a focusable widget."""
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    flow = make_flow("Test", n_phases=2)
    card = FlowCard(result=FlowResult(flow.name, ConfigStatus.OK, resolved=flow), index=0)
    assert card.can_focus is True


async def test_flow_card_carries_flow_config(make_flow):
    """FlowCard exposes the ResolvedFlow it was built from."""
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    flow = make_flow("Carrier", n_phases=2)
    card = FlowCard(result=FlowResult(flow.name, ConfigStatus.OK, resolved=flow), index=0)
    assert card.flow is flow


async def test_valid_flow_marker_uses_success_palette(make_flow):
    """The valid marker uses the established success color."""
    from ddev.cli.meta.ai.palette import SUCCESS
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    flow = make_flow("Valid", n_phases=1)
    card = FlowCard(result=FlowResult(flow.name, ConfigStatus.OK, resolved=flow), index=0)
    rendered = card.render()
    marker_index = rendered.plain.index("●")
    assert any(span.start <= marker_index < span.end and span.style == SUCCESS for span in rendered.spans)


async def test_flow_card_uses_available_width_before_truncating(make_flow, make_togo_app):
    name = "Openmetrics Integration Generator"
    flow = make_flow(name, n_phases=1)
    app = make_togo_app([flow])

    async with app.run_test(size=(240, 50)) as pilot:
        await pilot.pause()
        card = app.screen.query_one("FlowCard")

        assert card.content_region.width > len(name)
        assert card.render().plain.splitlines()[0] == name


async def test_flow_card_click_does_not_navigate_when_text_is_selected(monkeypatch, make_togo_app):
    """Releasing a drag selection over a card does not activate the card."""
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    app = make_togo_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        card = app.screen.query_one(FlowCard)
        monkeypatch.setattr(app.screen, "get_selected_text", lambda: "selected card text")

        card.on_click()
        await pilot.pause()

        assert isinstance(app.screen, MainScreen)


# ---------------------------------------------------------------------------
# MainScreen
# ---------------------------------------------------------------------------


async def test_main_screen_title():
    """MainScreen TITLE is set to the expected value."""
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    assert MainScreen.TITLE == "Flows"


async def test_main_screen_renders_flow_grid(make_flow, make_togo_app):
    """MainScreen includes a container with the #flow-grid id."""
    from textual.containers import VerticalScroll

    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    app = make_togo_app([make_flow("Alpha Flow", n_phases=3), make_flow("Beta Flow", n_phases=1)])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        pilot.app.screen.query_one("#flow-grid", VerticalScroll)


async def test_main_screen_empty_provider_no_cards(make_togo_app):
    """MainScreen with zero flows renders zero FlowCards."""
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    app = make_togo_app([])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        assert len(pilot.app.screen.query(FlowCard)) == 0


async def test_resume_discovery_uses_repository_root_when_cwd_differs(tmp_path, monkeypatch, make_flow, make_togo_app):
    """Dashboard and flow details discover runs below the configured repository."""
    from textual.widgets import Button

    from ddev.cli.meta.ai.tui.runs import flow_slug
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    repo_path = tmp_path / "repo"
    other_cwd = tmp_path / "elsewhere"
    repo_path.mkdir()
    other_cwd.mkdir()
    flow = make_flow("Repo Flow", n_phases=2)
    run_dir = repo_path / ".ddev" / "ai-runs" / flow_slug(flow)
    run_dir.mkdir(parents=True)
    (run_dir / "checkpoints.yaml").write_text(
        """phase_0:
  status: success
  started_at: '2024-01-01T00:00:00'
  finished_at: '2024-01-01T00:01:00'
  tokens:
    total_input: 1
    total_output: 1
  memory_path: phase_0_memory.md
"""
    )
    app = make_togo_app([flow])
    app.ddev_app.repo.path = str(repo_path)
    monkeypatch.chdir(other_cwd)

    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        card = app.screen.query_one(FlowCard)
        assert card.resumable
        card.action_select()
        await pilot.pause()
        assert isinstance(app.screen, FlowScreen)
        assert app.screen.query_one("#resume", Button).display
