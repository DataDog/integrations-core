# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""FlowCard widget — focusable card representing a single flow."""

from __future__ import annotations

from rich.text import Text
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static

from ddev.ai.config.models import ConfigStatus, FlowResult
from ddev.cli.meta.ai.palette import ERROR, SUCCESS
from ddev.cli.meta.ai.tui.widgets.pipeline_graph import COLOR_RUNNING

FLOW_DESCRIPTION_MAX_LINES = 2


class FlowCard(Static):
    """Focusable card for one validated or broken flow result."""

    can_focus = True

    BINDINGS = [Binding("enter", "select", "Select")]

    class Selected(Message):
        """Posted when the card is activated (Enter or click)."""

        def __init__(self, result: FlowResult) -> None:
            super().__init__()
            self.result = result

    def __init__(self, result: FlowResult, index: int, *, resumable: bool = False) -> None:
        classes = "broken" if result.status is ConfigStatus.BROKEN else "valid"
        super().__init__(classes=classes)
        self.result = result
        self.flow = result.resolved
        self.index = index
        self.resumable = resumable

    @property
    def phase_count(self) -> int:
        """Number of phases in the flow."""
        return len(self.flow.flow) if self.flow is not None else 0

    def render(self) -> Text:
        name = self.result.name or "(unnamed)"
        desc = self.flow.description if self.flow is not None and self.flow.description else ""
        if self.result.status is ConfigStatus.BROKEN:
            desc = self.result.errors[0].message if self.result.errors else "Invalid flow configuration"
        n = self.phase_count
        content = Text(name, style="bold", no_wrap=True, overflow="ellipsis")
        if desc:
            content.append("\n")
            content.append_text(self._render_description(desc))
        content.append("\n\n")
        if self.result.status is ConfigStatus.BROKEN:
            count = len(self.result.errors)
            content.append(
                f"✕ broken · {count} {'error' if count == 1 else 'errors'}",
                style=f"bold {ERROR}",
            )
            content.append("\nEnter to inspect diagnostics", style="dim")
        else:
            phase_word = "phase" if n == 1 else "phases"
            content.append("●", style=SUCCESS)
            content.append(f" {n} {phase_word}")
            if self.resumable:
                content.append("\n↻ resumable run available", style=COLOR_RUNNING)
        return content

    def _render_description(self, description: str) -> Text:
        width = self.content_size.width
        if width <= 0:
            return Text(description, style="dim")

        lines = Text(description, style="dim").wrap(self.app.console, width)
        visible_lines = lines[:FLOW_DESCRIPTION_MAX_LINES]
        if len(lines) > FLOW_DESCRIPTION_MAX_LINES:
            last_line = visible_lines[-1]
            last_line.truncate(max(width - 1, 0))
            last_line.append("…", style="dim")
        return Text("\n").join(visible_lines)

    def action_select(self) -> None:
        self.post_message(self.Selected(self.result))

    def on_click(self) -> None:
        if self.screen.get_selected_text():
            return
        self.post_message(self.Selected(self.result))
