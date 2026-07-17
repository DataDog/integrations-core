# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""TogoScreen — base screen providing the shared chrome (header + rule + body + footer)."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterator
from typing import cast

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer

from ddev.cli.meta.ai.tui.app import TogoApp
from ddev.cli.meta.ai.tui.widgets.header import TogoHeader


class TogoScreen(Screen):
    """Base screen composing TogoHeader + compose_body() + Footer."""

    def __init__(self) -> None:
        super().__init__()
        self._togo_title: str | None = None

    def compose(self) -> ComposeResult:
        yield TogoHeader(title=self._togo_title or self.TITLE or "")
        with Container(id="screen-body"):
            yield from self.compose_body()
        yield Footer()

    @property
    def togo_app(self) -> TogoApp:
        """Return the concrete app this screen is mounted under."""
        return cast(TogoApp, self.app)

    def copy_selection(self) -> bool:
        """Copy the current screen selection, returning whether text was available."""
        selection = self.get_selected_text()
        if not selection:
            return False
        self.app.copy_to_clipboard(selection)
        return True

    @abstractmethod
    def compose_body(self) -> Iterator[Widget]:
        """Yield the screen-specific body widgets."""
