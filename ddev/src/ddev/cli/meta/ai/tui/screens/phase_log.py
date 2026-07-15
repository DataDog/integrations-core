# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Full-screen phase log view."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Protocol

from rich.console import RenderableType
from rich.markdown import Markdown as RichMarkdown
from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Markdown, Static

from ddev.ai.config.models import ResolvedFlow
from ddev.cli.meta.ai.tui.screens.base import TogoScreen
from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

type PhaseLogEntry = str | Text | Panel | RichMarkdown

SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def _selectable_widget(renderable: RenderableType) -> Widget:
    if isinstance(renderable, RichMarkdown):
        return Markdown(renderable.markup, classes="phase-log-markdown")
    if isinstance(renderable, Panel):
        return PhaseLogPanel(renderable)
    return Static(renderable)


class PhaseLogPanel(Vertical):
    """Selectable Textual equivalent of a Rich panel."""

    def __init__(self, panel: Panel) -> None:
        super().__init__(classes="phase-log-panel")
        self._panel = panel
        if panel.title is not None:
            self.border_title = str(panel.title)
        if str(panel.border_style) != "none":
            self.styles.border = ("round", str(panel.border_style))

    def compose(self) -> ComposeResult:
        yield _selectable_widget(self._panel.renderable)


class PhaseLogBlock(Vertical):
    """A single rendered block in the phase log."""

    def __init__(self, renderable: PhaseLogEntry) -> None:
        super().__init__(classes="phase-log-block")
        self._renderable = renderable

    def compose(self) -> ComposeResult:
        yield _selectable_widget(self._renderable)


class ThinkingBlock(Static):
    """Transient block shown while an agent response is pending."""

    frame: reactive[int] = reactive(0)

    def __init__(self, key: str, label: str) -> None:
        super().__init__("", classes="phase-log-block phase-log-thinking")
        self.key = key
        self._label = label

    def on_mount(self) -> None:
        self.set_interval(0.1, self._tick)
        self._update()

    def watch_frame(self, frame: int) -> None:
        self._update()

    def _tick(self) -> None:
        self.frame = (self.frame + 1) % len(SPINNER_FRAMES)

    def _update(self) -> None:
        self.update(f"{SPINNER_FRAMES[self.frame]} thinking · {self._label}")


class PhaseLogSource(Protocol):
    """Object that tracks open phase log screens for live writes."""

    def register_phase_log_screen(self, screen: PhaseLogScreen) -> None: ...

    def unregister_phase_log_screen(self, screen: PhaseLogScreen) -> None: ...


class PhaseLogScreen(TogoScreen):
    """Shows the live log for one running phase."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+c", "copy_or_show_config", "Copy / Config"),
    ]

    def __init__(
        self,
        flow: ResolvedFlow,
        phase_id: str,
        entries: Sequence[PhaseLogEntry],
        source: PhaseLogSource | None = None,
    ) -> None:
        super().__init__()
        self.flow = flow
        self.phase_id = phase_id
        self._entries = entries
        self._source = source
        self._replayed_entries = False
        self._written_entry_ids: set[int] = set()
        self._thinking_blocks: dict[str, ThinkingBlock] = {}
        self._togo_title = f"{flow.name or 'Flow'} · {phase_id} log"

    def compose_body(self) -> Iterator[Widget]:
        yield VerticalScroll(id="phase-log-output")

    def on_mount(self) -> None:
        self._replay_entries()
        if self._source is not None:
            self._source.register_phase_log_screen(self)

    def on_unmount(self) -> None:
        if self._source is not None:
            self._source.unregister_phase_log_screen(self)

    def write(self, renderable: PhaseLogEntry) -> None:
        try:
            output = self.query_one("#phase-log-output", VerticalScroll)
            should_scroll = output.is_vertical_scroll_end
            output.mount(PhaseLogBlock(renderable))
            if should_scroll:
                output.call_after_refresh(output.scroll_end, animate=False)
            self._written_entry_ids.add(id(renderable))
        except Exception:
            pass

    def start_thinking(self, key: str, label: str) -> None:
        try:
            output = self.query_one("#phase-log-output", VerticalScroll)
        except Exception:
            return
        if key in self._thinking_blocks:
            return
        block = ThinkingBlock(key, label)
        self._thinking_blocks[key] = block
        should_scroll = output.is_vertical_scroll_end
        output.mount(block)
        if should_scroll:
            output.call_after_refresh(output.scroll_end, animate=False)

    def stop_thinking(self, key: str) -> None:
        block = self._thinking_blocks.pop(key, None)
        if block is not None and block.is_mounted:
            block.remove()

    def _replay_entries(self, retry: bool = True) -> bool:
        if self._replayed_entries:
            return True

        for entry in self._entries:
            if id(entry) not in self._written_entry_ids:
                self.write(entry)
        self._replayed_entries = True
        return True

    def action_show_config(self) -> None:
        self.app.push_screen(PhaseConfigScreen(self.flow, self.phase_id))

    def action_copy_or_show_config(self) -> None:
        if not self.copy_selection():
            self.action_show_config()
