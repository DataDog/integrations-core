# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for tui/app.py: TogoApp structural and behavioral properties."""

from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace

from textual.app import App


async def test_togo_app_boots_with_main_screen(make_togo_app):
    """The app pushes MainScreen on mount so it is the active screen."""
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    app = make_togo_app([])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)


async def test_togo_app_does_not_offer_command_palette(make_togo_app):
    """The footer and keyboard shortcuts expose only Togo actions."""
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    app = make_togo_app([])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert "palette" not in app.export_screenshot().lower()

        await pilot.press("ctrl+p")
        await pilot.pause()
        assert isinstance(app.screen, MainScreen)


async def test_bridge_target_defaults_to_app(make_togo_app):
    app = make_togo_app([])
    async with app.run_test():
        assert app.bridge_target is app


async def test_received_sink_starts_empty(make_togo_app):
    app = make_togo_app([])
    async with app.run_test():
        assert app.received == []


async def test_copy_to_clipboard_uses_system_and_textual_clipboards(monkeypatch, make_togo_app):
    copied: list[str] = []
    monkeypatch.setitem(sys.modules, "pyperclip", SimpleNamespace(copy=copied.append))

    app = make_togo_app([])
    async with app.run_test():
        app.copy_to_clipboard("selected output")

        assert copied == ["selected output"]
        assert app.clipboard == "selected output"


async def test_copy_to_clipboard_ignores_textual_clipboard_failure(monkeypatch, make_togo_app):
    copied: list[str] = []
    monkeypatch.setitem(sys.modules, "pyperclip", SimpleNamespace(copy=copied.append))

    def fail_textual_copy(_app: App, _text: str) -> None:
        raise RuntimeError("OSC 52 unavailable")

    monkeypatch.setattr(App, "copy_to_clipboard", fail_textual_copy)
    app = make_togo_app([])
    async with app.run_test():
        app.copy_to_clipboard("selected output")

        assert copied == ["selected output"]


async def test_copy_to_clipboard_falls_back_when_system_clipboard_fails(monkeypatch, make_togo_app):
    native_copies: list[tuple[list[str], str]] = []

    def fail_system_copy(_text: str) -> None:
        raise RuntimeError("system clipboard unavailable")

    def native_copy(command: list[str], *, input: str, text: bool, check: bool) -> None:
        assert text is True
        assert check is True
        native_copies.append((command, input))

    app_module = importlib.import_module("ddev.cli.meta.ai.tui.app")
    monkeypatch.setitem(sys.modules, "pyperclip", SimpleNamespace(copy=fail_system_copy))
    monkeypatch.setattr(app_module.subprocess, "run", native_copy)
    monkeypatch.setattr(app_module.sys, "platform", "darwin")
    app = make_togo_app([])
    async with app.run_test():
        app.copy_to_clipboard("selected output")

        assert native_copies == [(["/usr/bin/pbcopy"], "selected output")]
        assert app.clipboard == "selected output"


async def test_text_selection_is_copied_automatically(monkeypatch, make_togo_app):
    copied: list[str] = []
    app = make_togo_app([])
    async with app.run_test() as pilot:
        await pilot.pause()
        monkeypatch.setattr(app.screen, "get_selected_text", lambda: "selected output")
        monkeypatch.setattr(app, "copy_to_clipboard", copied.append)

        app.on_text_selected()

        assert copied == ["selected output"]
