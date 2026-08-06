# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""FlowCard widget — focusable card representing a single flow."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ddev.ai.config.models import ConfigStatus, FlowResult
from ddev.ai.runtime.checkpoints import ResumeState
from ddev.cli.meta.ai.palette import ERROR, SUCCESS
from ddev.cli.meta.ai.tui.widgets.pipeline_graph import COLOR_RUNNING


class FlowCardDescription(Static):
    """Flow description that marks clipped text with an ellipsis."""

    def __init__(self, description: str) -> None:
        super().__init__(description, classes="flow-card-description", markup=False)
        self.description = description

    def render(self) -> Text:
        width, height = self.content_size
        if width <= 0 or height <= 0:
            return Text(self.description)

        lines = Text(self.description).wrap(self.app.console, width)
        if len(lines) <= height:
            return Text("\n").join(lines)

        visible_lines = lines[:height]
        last_line = visible_lines[-1]
        last_line.truncate(max(width - 3, 0))
        last_line.append("...")
        return Text("\n").join(visible_lines)


class FlowCard(Widget):
    """Focusable card for one validated or broken flow result."""

    can_focus = True

    BINDINGS = [Binding("enter", "select", "Select")]

    # Recomposes rather than repaints: the resume line lives in the footer child, which a
    # repaint of the card would not rebuild.
    resume_state: reactive[ResumeState] = reactive(ResumeState(), init=False, recompose=True)

    class Selected(Message):
        """Posted when the card is activated (Enter or click)."""

        def __init__(self, result: FlowResult) -> None:
            super().__init__()
            self.result = result

    def __init__(self, result: FlowResult, index: int, *, resume_state: ResumeState | None = None) -> None:
        classes = "broken" if result.status is ConfigStatus.BROKEN else "valid"
        super().__init__(classes=classes)
        self.result = result
        self.flow = result.resolved
        self.index = index
        self.set_reactive(FlowCard.resume_state, resume_state or ResumeState())

    @property
    def resumable(self) -> bool:
        """Whether the recorded run leaves something for a resume to do."""
        return self.resume_state.is_resumable

    @property
    def phase_count(self) -> int:
        """Number of phases in the flow."""
        return len(self.flow.flow) if self.flow is not None else 0

    def compose(self) -> ComposeResult:
        name = self.result.name or "(unnamed)"
        desc = self.flow.description if self.flow is not None and self.flow.description else ""
        if self.result.status is ConfigStatus.BROKEN:
            desc = self.result.errors[0].message if self.result.errors else "Invalid flow configuration"

        yield Static(name, classes="flow-card-name", markup=False)
        if desc:
            yield FlowCardDescription(desc)
        yield Static(self._render_footer(), classes="flow-card-footer")

    def _render_footer(self) -> Text:
        content = Text()
        if self.result.status is ConfigStatus.BROKEN:
            count = len(self.result.errors)
            content.append(
                f"✕ broken · {count} {'error' if count == 1 else 'errors'}",
                style=f"bold {ERROR}",
            )
            content.append("\nEnter to inspect diagnostics", style="dim")
        else:
            n = self.phase_count
            phase_word = "phase" if n == 1 else "phases"
            content.append("●", style=SUCCESS)
            content.append(f" {n} {phase_word}")
            if self.resume_state.error is not None:
                content.append("\n✕ checkpoint unreadable", style=ERROR)
            elif self.resumable:
                content.append("\n↻ resumable run available", style=COLOR_RUNNING)
        return content

    def action_select(self) -> None:
        self.post_message(self.Selected(self.result))

    def on_click(self) -> None:
        if self.screen.get_selected_text():
            return
        self.post_message(self.Selected(self.result))
