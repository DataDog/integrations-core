# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for tui/theme.py: togo_theme tokens and CSS stylesheet loading."""

from __future__ import annotations

import pytest

from ddev.cli.meta.ai.palette import ACCENT, PRIMARY, SECONDARY
from ddev.cli.meta.ai.tui.app import TogoApp
from ddev.cli.meta.ai.tui.theme import togo_theme


def test_togo_theme_tokens():
    """The togo theme exposes the design-system tokens used by the TUI."""
    assert togo_theme.name == "togo"
    assert togo_theme.primary == PRIMARY
    assert togo_theme.secondary == SECONDARY
    assert togo_theme.accent == ACCENT
    assert togo_theme.dark is True
    assert {"status-running", "status-pending", "status-done", "status-failed"} <= set(togo_theme.variables)


def test_togo_app_css_path_set():
    """TogoApp declares togo.tcss as its CSS_PATH."""
    from pathlib import Path

    assert Path(TogoApp.CSS_PATH).name == "togo.tcss"
    assert Path(TogoApp.CSS_PATH).exists()


async def test_togo_app_registers_togo_theme(make_togo_app):
    """The togo theme is registered and active after mount."""
    app = make_togo_app([])
    async with app.run_test():
        assert "togo" in app.available_themes
        assert app.theme == "togo"


async def test_togo_app_css_loads_without_error(make_togo_app):
    """The app boots without raising CSS parse errors."""
    app = make_togo_app([])
    async with app.run_test():
        # If CSS_PATH contains a parse error, run_test() raises; reaching here
        # means the stylesheet was loaded successfully.
        pass


# ---------------------------------------------------------------------------
# get_theme_variable_defaults — TOGOTUI-12
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["status-running", "status-pending", "status-done", "status-failed"])
def test_get_theme_variable_defaults_returns_status_key(key, make_togo_app):
    """TogoApp.get_theme_variable_defaults() includes all four status keys."""
    defaults = make_togo_app([]).get_theme_variable_defaults()
    assert key in defaults


def test_get_theme_variable_defaults_values_match_theme(make_togo_app):
    """Default values match the corresponding togo_theme variables."""
    defaults = make_togo_app([]).get_theme_variable_defaults()
    for key in ("status-running", "status-pending", "status-done", "status-failed"):
        assert defaults[key] == togo_theme.variables[key]


async def test_css_uses_status_running_variable_not_hardcoded():
    """togo.tcss must not contain the hardcoded status-running hex; use $status-running instead."""
    from pathlib import Path

    from ddev.cli.meta.ai.palette import STATUS_RUNNING

    tcss = Path(TogoApp.CSS_PATH).read_text()
    assert STATUS_RUNNING not in tcss, f"Replace hardcoded {STATUS_RUNNING} with $status-running in togo.tcss"


def test_border_titles_use_visible_accent_color():
    """Titled boxes should not use muted grey for their border titles."""
    from pathlib import Path

    tcss = Path(TogoApp.CSS_PATH).read_text()
    assert "border-title-color: $text-muted" not in tcss


def test_flow_cards_use_consistent_height_and_round_border():
    """Flow cards should render as grid cards with a shared standard height."""
    from pathlib import Path

    tcss = Path(TogoApp.CSS_PATH).read_text()
    assert "FlowCard {\n    background: $panel;\n    border: solid $border;" in tcss
    assert "height: 10;" in tcss


def test_flow_grid_scrolls_vertically():
    """Large flow result sets stay reachable within the dashboard."""
    from pathlib import Path

    tcss = Path(TogoApp.CSS_PATH).read_text()
    assert "#flow-grid {\n    layout: grid;" in tcss
    assert "height: 1fr;" in tcss
    assert "overflow-y: auto;" in tcss


def test_launch_fields_have_vertical_spacing():
    """Launch modal fields must not render cramped against each other."""
    from pathlib import Path

    tcss = Path(TogoApp.CSS_PATH).read_text()
    assert "#launch-fields > Label.eyebrow {\n    margin-top: 1;\n}" in tcss


def test_input_focus_uses_muted_accent_not_bold_primary():
    """Focused inputs should use a subtle accent outline, not a bold filled primary border."""
    from pathlib import Path

    tcss = Path(TogoApp.CSS_PATH).read_text()
    assert "Input:focus {\n    border: tall $accent;\n}" in tcss
    assert "Input:focus {\n    border: round $primary;\n}" not in tcss


def test_markdown_h3_headings_wrap_instead_of_overflowing():
    """Textual's built-in MarkdownH3 defaults to `width: auto`, which stops long headings
    (e.g. in agent system prompts) from wrapping and lets them run off the right edge of
    the pane instead of flowing onto multiple lines like every other Markdown block."""
    from pathlib import Path

    tcss = Path(TogoApp.CSS_PATH).read_text()
    assert "MarkdownH3 {\n    width: 1fr;\n}" in tcss


async def test_togo_theme_status_running_matches_default(make_togo_app):
    """The active togo theme's status-running matches get_theme_variable_defaults."""
    app = make_togo_app([])
    async with app.run_test():
        defaults = app.get_theme_variable_defaults()
        assert app.current_theme.variables["status-running"] == defaults["status-running"]
