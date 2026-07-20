# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the app shell: bindings, dependency injection, shared chrome, and header."""

from __future__ import annotations

from typing import Any

import pytest
from textual.widgets import Footer

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.errors import ErrorKind, FlowError
from ddev.ai.config.models import ConfigStatus, FlowResult
from ddev.ai.phases.registry import PhaseRegistry
from ddev.cli.meta.ai.tui.app import TogoApp
from ddev.cli.meta.ai.tui.screens.base import TogoScreen
from ddev.cli.meta.ai.tui.status import ExecutionStatus
from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge, TogoHeader

from .conftest import StaticConfigurationEngine


def _app_kwargs(ddev_app):
    return {
        "engine": StaticConfigurationEngine([]),
        "phase_registry": PhaseRegistry(),
        "provider_registry": AgentProviderRegistry(),
        "ddev_app": ddev_app,
    }


# ---------------------------------------------------------------------------
# Global bindings
# ---------------------------------------------------------------------------


async def test_ctrl_q_is_bound_globally(ddev_app):
    """ctrl+q is bound at the App level."""
    app = TogoApp(**_app_kwargs(ddev_app))
    async with app.run_test():
        keys = {b.key for b in app.BINDINGS}
        assert "ctrl+q" in keys


# ---------------------------------------------------------------------------
# Configuration dependency injection
# ---------------------------------------------------------------------------


async def test_togo_app_accepts_configuration_dependencies(ddev_app):
    """TogoApp stores the injected engine and registries."""
    kwargs = _app_kwargs(ddev_app)
    app = TogoApp(**kwargs)
    async with app.run_test():
        assert app.engine is kwargs["engine"]
        assert app.phase_registry is kwargs["phase_registry"]
        assert app.provider_registry is kwargs["provider_registry"]


# ---------------------------------------------------------------------------
# TogoScreen base chrome
# ---------------------------------------------------------------------------


class _DummyScreen(TogoScreen):
    """Minimal concrete TogoScreen for testing the base class chrome."""

    TITLE = "Test Screen"

    def compose_body(self):
        from textual.widgets import Label

        yield Label("body content", id="dummy-body-content")


class _DummyApp(TogoApp):
    """TogoApp variant that boots directly into _DummyScreen."""

    def on_mount(self) -> None:
        from ddev.cli.meta.ai.tui.theme import togo_theme

        self.register_theme(togo_theme)
        self.theme = "togo"
        self.push_screen(_DummyScreen())


@pytest.mark.parametrize("widget_cls", [TogoHeader, Footer], ids=["header", "footer"])
async def test_togo_screen_contains_chrome_widget(widget_cls, ddev_app):
    """TogoScreen renders header and footer chrome widgets."""
    async with _DummyApp(**_app_kwargs(ddev_app)).run_test() as pilot:
        await pilot.pause()
        assert pilot.app.screen.query_one(widget_cls)


async def test_togo_screen_wraps_body_in_shared_region(ddev_app):
    """TogoScreen renders screen-specific content inside the shared padded body."""
    async with TogoApp(**_app_kwargs(ddev_app)).run_test() as pilot:
        await pilot.pause()
        body = pilot.app.screen.query_one("#screen-body")
        assert body.query_one("#flow-grid")


# ---------------------------------------------------------------------------
# TogoHeader widget
# ---------------------------------------------------------------------------


async def test_togo_header_displays_husky_mascot(ddev_app):
    """The application header visibly identifies Togo and its repository."""
    async with _DummyApp(**_app_kwargs(ddev_app)).run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screenshot = pilot.app.export_screenshot()

        assert "█▀▄" in screenshot
        assert "▀▀███▀▀" in screenshot
        assert "Togo" in screenshot
        assert "Agent&#160;Integrations" in screenshot
        assert "0&#160;Flows&#160;Discovered" in screenshot
        assert str(ddev_app.repo.path) in screenshot


async def test_togo_header_calls_attention_to_broken_flows(ddev_app):
    """Broken flows are summarized prominently in the application header."""
    kwargs = _app_kwargs(ddev_app)
    kwargs["engine"] = StaticConfigurationEngine(
        [],
        results=[
            FlowResult(
                "Broken Flow",
                ConfigStatus.BROKEN,
                [FlowError(ErrorKind.FLOW, "invalid configuration")],
            )
        ],
    )
    async with _DummyApp(**kwargs).run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        assert "1&#160;flows&#160;need&#160;attention" in pilot.app.export_screenshot()


async def test_togo_header_running_badge_pulses(ddev_app):
    """The running badge is visible and alternates its marker."""
    async with _DummyApp(**_app_kwargs(ddev_app)).run_test() as pilot:
        await pilot.pause()
        badge = pilot.app.screen.query_one(ExecutionStatusBadge)

        pilot.app.execution_status = ExecutionStatus.RUNNING
        await pilot.pause(0.1)
        first = str(badge.render())
        await pilot.pause(0.7)
        second = str(badge.render())

    assert first in {"● running", "○ running"}
    assert second in {"● running", "○ running"}
    assert first != second


async def test_togo_header_idle_badge_is_empty(ddev_app: Any) -> None:
    """Non-execution headers do not show a lifecycle badge."""
    async with _DummyApp(**_app_kwargs(ddev_app)).run_test() as pilot:
        await pilot.pause()
        badge = pilot.app.screen.query_one(ExecutionStatusBadge)

        assert str(badge.render()) == ""


@pytest.mark.parametrize(
    ("status", "label"),
    [
        (ExecutionStatus.FINISHING, "◌ finishing"),
        (ExecutionStatus.COMPLETED, "✓ completed"),
        (ExecutionStatus.FAILED, "✕ failed"),
    ],
)
async def test_togo_header_stable_execution_badges(ddev_app: Any, status: ExecutionStatus, label: str) -> None:
    """Terminal and finishing states have stable visible labels."""
    async with _DummyApp(**_app_kwargs(ddev_app)).run_test() as pilot:
        await pilot.pause()
        badge = pilot.app.screen.query_one(ExecutionStatusBadge)

        pilot.app.execution_status = status
        await pilot.pause()

        assert str(badge.render()) == label


async def test_new_screen_header_shows_current_execution_status(ddev_app: Any) -> None:
    """Screens opened during a run retain the app-wide execution status."""
    async with _DummyApp(**_app_kwargs(ddev_app)).run_test() as pilot:
        await pilot.pause()
        pilot.app.execution_status = ExecutionStatus.FINISHING
        await pilot.app.push_screen(_DummyScreen())
        await pilot.pause()

        badge = pilot.app.screen.query_one(ExecutionStatusBadge)
        assert str(badge.render()) == "◌ finishing"
