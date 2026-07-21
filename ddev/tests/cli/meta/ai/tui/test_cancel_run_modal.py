# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the active-flow cancellation confirmation modal."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult

from .conftest import TogoModalTestApp


class CancelRunModalTestApp(TogoModalTestApp):
    """Minimal app that records a CancelRunModal dismissal."""

    def __init__(self) -> None:
        super().__init__()
        self.dismiss_result: Any = "NOT_SET"

    def compose(self) -> ComposeResult:
        yield from []

    def on_mount(self) -> None:
        from ddev.cli.meta.ai.tui.screens.cancel_run_modal import CancelRunModal

        self.push_screen(CancelRunModal(), lambda result: setattr(self, "dismiss_result", result))


async def test_cancel_run_modal_escape_keeps_running() -> None:
    """Escape dismisses the modal with the non-cancelling result."""
    app = CancelRunModalTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.dismiss_result is False


async def test_cancel_run_modal_keep_running_button_dismisses_safely() -> None:
    """The safe button dismisses the modal with the non-cancelling result."""
    app = CancelRunModalTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#btn-keep-running")
        await pilot.pause()
        assert app.dismiss_result is False


async def test_cancel_run_modal_cancel_button_confirms() -> None:
    """The destructive button dismisses the modal with True."""
    app = CancelRunModalTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#btn-cancel-flow")
        await pilot.pause()
        assert app.dismiss_result is True
