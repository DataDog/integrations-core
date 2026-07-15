# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Reusable pipeline DAG graph widgets."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TypedDict, Unpack

from rich.text import Text
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.geometry import Offset
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from ddev.ai.config.models import ResolvedFlow
from ddev.cli.meta.ai.palette import STATUS_CONNECTOR, STATUS_DONE, STATUS_FAILED, STATUS_PENDING, STATUS_RUNNING
from ddev.cli.meta.ai.tui.status import RunStatus

COLOR_DONE = STATUS_DONE
COLOR_RUNNING = STATUS_RUNNING
COLOR_PENDING = STATUS_PENDING
COLOR_FAILED = STATUS_FAILED
COLOR_CONNECTOR = STATUS_CONNECTOR
GRAPH_COLUMN_GAP = 6
GRAPH_ROW_GAP = 5
NODE_HEIGHT = 3  # keep in sync with the `.phase-node` height in togo.tcss


class WidgetKwargs(TypedDict, total=False):
    name: str | None
    id: str | None
    classes: str | None
    disabled: bool
    markup: bool


NODE_GLYPHS: dict[RunStatus, tuple[str, str]] = {
    RunStatus.DONE: ("○", COLOR_DONE),
    RunStatus.RUNNING: ("◉", COLOR_RUNNING),
    RunStatus.FAILED: ("✕", COLOR_FAILED),
}


@dataclass(frozen=True)
class _GraphNode:
    phase_id: str
    status: RunStatus
    label: str
    color: str
    x: int
    y: int


@dataclass(frozen=True)
class _PipelineLayout:
    connectors: Text
    nodes: list[_GraphNode]


class PhaseSelected(Message):
    """Posted when a graph phase node is activated."""

    def __init__(self, phase_id: str) -> None:
        super().__init__()
        self.phase_id = phase_id


def _phase_label(phase_id: str, statuses: dict[str, RunStatus]) -> tuple[str, str]:
    status = statuses.get(phase_id, RunStatus.PENDING)
    glyph, color = NODE_GLYPHS.get(status, ("●", COLOR_PENDING))
    return f"{glyph} {phase_id}", color


def _pad_labels(labels: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Right-pad every label to the same width so all boxes render at a uniform size."""
    if not labels:
        return labels
    width = max(len(text) for text, _ in labels.values())
    return {phase_id: (text.ljust(width), color) for phase_id, (text, color) in labels.items()}


def _display_dependencies(flow: ResolvedFlow) -> dict[str, list[str]]:
    deps_by_phase = {entry.phase: entry.dependencies for entry in flow.flow}

    def depends_on(phase_id: str, dependency: str, seen: set[str] | None = None) -> bool:
        if seen is None:
            seen = set()
        if phase_id in seen:
            return False
        seen.add(phase_id)
        deps = deps_by_phase.get(phase_id, [])
        return dependency in deps or any(depends_on(dep, dependency, seen) for dep in deps)

    display_deps: dict[str, list[str]] = {}
    for entry in flow.flow:
        deps = entry.dependencies
        display_deps[entry.phase] = [
            dep for dep in deps if not any(other != dep and depends_on(other, dep) for other in deps)
        ]
    return display_deps


def _phase_levels(flow: ResolvedFlow, deps_by_phase: dict[str, list[str]]) -> dict[str, int]:
    levels: dict[str, int] = {}

    def level_for(phase_id: str) -> int:
        if phase_id in levels:
            return levels[phase_id]
        deps = deps_by_phase.get(phase_id, [])
        level = 0 if not deps else 1 + max(level_for(dep) for dep in deps)
        levels[phase_id] = level
        return level

    for entry in flow.flow:
        level_for(entry.phase)
    return levels


def _phase_positions(
    flow: ResolvedFlow,
    levels: dict[str, int],
    deps_by_phase: dict[str, list[str]],
    labels: dict[str, tuple[str, str]],
) -> dict[str, tuple[int, int]]:
    """Lay phases out in an evenly spaced grid, then center parents over children.

    ``labels`` are pre-padded to a common width (see ``_pad_labels``), so every
    box is the same size and a plain left-edge x is interchangeable with a
    box center for averaging purposes. The layout runs in two passes:

    1. Top-down: seed each level with an evenly spaced, left-to-right row in
       the flow's declared order.
    2. Bottom-up: starting at the deepest level, pull every node toward the
       mean x of its direct children (the phases that depend on it), then
       re-sweep the level left-to-right to restore the minimum column gap
       that centering may have collapsed. This settles parents over the
       midpoint of their children instead of hugging whichever sibling
       happened to be laid out first.
    """
    entries_by_level: dict[int, list[str]] = {}
    for entry in flow.flow:
        entries_by_level.setdefault(levels[entry.phase], []).append(entry.phase)

    if not entries_by_level:
        return {}

    box_width = len(next(iter(labels.values()))[0])
    step = box_width + GRAPH_COLUMN_GAP

    children_of: dict[str, list[str]] = {phase_id: [] for phase_id in labels}
    for phase_id, deps in deps_by_phase.items():
        for dep in deps:
            children_of[dep].append(phase_id)

    x: dict[str, float] = {}
    for level in sorted(entries_by_level):
        for index, phase_id in enumerate(entries_by_level[level]):
            x[phase_id] = float(index * step)

    for level in sorted(entries_by_level, reverse=True):
        row = entries_by_level[level]
        for phase_id in row:
            kids = children_of[phase_id]
            if kids:
                x[phase_id] = sum(x[kid] for kid in kids) / len(kids)

        previous_edge: float | None = None
        for phase_id in sorted(row, key=lambda phase_id: x[phase_id]):
            if previous_edge is not None and x[phase_id] < previous_edge:
                x[phase_id] = previous_edge
            previous_edge = x[phase_id] + step

    min_x = min(x.values())
    return {
        phase_id: (round(x[phase_id] - min_x), level * GRAPH_ROW_GAP)
        for level, row in entries_by_level.items()
        for phase_id in row
    }


def _draw_char(grid: list[list[str]], y: int, x: int, char: str) -> None:
    if y < 0 or x < 0 or y >= len(grid) or x >= len(grid[y]):
        return
    existing = grid[y][x]
    corners = {"┐", "┘", "┌", "└"}
    if existing == " " or existing == char:
        grid[y][x] = char
    elif char in {"▶", "▼"}:
        grid[y][x] = char
    elif existing in {"▶", "▼"}:
        return
    elif existing in corners and char == "─":
        grid[y][x] = "┬" if existing in {"┐", "┌"} else "┴"
    elif existing in {"┬", "┴"} and char in {"│", "─"}:
        return
    elif existing in corners and char == "│":
        return
    elif char in corners and existing == "─":
        grid[y][x] = "┬" if char in {"┐", "┌"} else "┴"
    elif char in corners and existing == "│":
        grid[y][x] = char
    elif {existing, char} <= {"─", "│"}:
        grid[y][x] = "┼"
    else:
        grid[y][x] = "┼"


def _draw_horizontal(grid: list[list[str]], y: int, start_x: int, end_x: int) -> None:
    if end_x < start_x:
        return
    for x in range(start_x, end_x + 1):
        _draw_char(grid, y, x, "─")


def _draw_vertical(grid: list[list[str]], x: int, start_y: int, end_y: int) -> None:
    if end_y < start_y:
        start_y, end_y = end_y, start_y
    for y in range(start_y, end_y + 1):
        _draw_char(grid, y, x, "│")


def _draw_edge(grid: list[list[str]], start: tuple[int, int], end: tuple[int, int]) -> None:
    start_x, start_y = start
    end_x, end_y = end
    if end_y <= start_y:
        return

    arrow_y = end_y - 1
    if start_x == end_x:
        _draw_vertical(grid, start_x, start_y, arrow_y - 1)
        _draw_char(grid, arrow_y, start_x, "▼")
        return

    mid_y = start_y + 1
    _draw_vertical(grid, start_x, start_y, mid_y - 1)
    _draw_char(grid, mid_y, start_x, "└" if end_x > start_x else "┘")
    _draw_horizontal(grid, mid_y, min(start_x, end_x) + 1, max(start_x, end_x) - 1)
    _draw_char(grid, mid_y, end_x, "┐" if end_x > start_x else "┌")
    _draw_vertical(grid, end_x, mid_y + 1, arrow_y - 1)
    _draw_char(grid, arrow_y, end_x, "▼")


def render_pipeline(flow: ResolvedFlow, statuses: dict[str, RunStatus]) -> Text:
    """Build a Rich Text dependency graph from declared flow edges."""
    layout = _build_pipeline_layout(flow, statuses)
    lines = layout.connectors.plain.splitlines() or [""]
    grid = [list(line) for line in lines]
    width = max((len(line) for line in lines), default=0)
    for line in grid:
        line.extend(" " for _ in range(width - len(line)))

    node_ranges: list[tuple[int, int, int, str]] = []
    for node in layout.nodes:
        while node.y >= len(grid):
            grid.append([" " for _ in range(width)])
        if node.x + len(node.label) > width:
            for line in grid:
                line.extend(" " for _ in range(node.x + len(node.label) - width))
            width = node.x + len(node.label)
        for offset, char in enumerate(node.label):
            grid[node.y][node.x + offset] = char
        node_ranges.append((node.y, node.x, node.x + len(node.label), node.color))

    result_lines = ["".join(line).rstrip() for line in grid]
    result = Text("\n".join(result_lines))
    offset = 0
    for line_number, result_line in enumerate(result_lines):
        for node_y, start_x, end_x, color in node_ranges:
            if node_y == line_number:
                result.stylize(color, offset + start_x, offset + end_x)
        for index, char in enumerate(result_line):
            if char in "─│┐┘┌└┼▶▼┬┴":
                result.stylize(COLOR_CONNECTOR, offset + index, offset + index + 1)
        offset += len(result_line) + 1
    return result


def _build_pipeline_layout(flow: ResolvedFlow, statuses: dict[str, RunStatus]) -> _PipelineLayout:
    entries = flow.flow
    if not entries:
        return _PipelineLayout(Text(), [])

    deps_by_phase = _display_dependencies(flow)
    levels = _phase_levels(flow, deps_by_phase)
    labels = _pad_labels({entry.phase: _phase_label(entry.phase, statuses) for entry in entries})
    node_positions = _phase_positions(flow, levels, deps_by_phase, labels)
    height = max(y for _, y in node_positions.values()) + 1
    width = max(x + len(labels[entry.phase][0]) for entry in entries for x, _ in [node_positions[entry.phase]])
    grid = [[" " for _ in range(width)] for _ in range(height)]

    for entry in entries:
        end_x, end_y = node_positions[entry.phase]
        end_label = labels[entry.phase][0]
        for dep in deps_by_phase[entry.phase]:
            start_x, start_y = node_positions[dep]
            start_label = labels[dep][0]
            _draw_edge(
                grid,
                # Anchor at the node's bottom border row rather than its middle: any
                # segment drawn inside the box's own rows is invisible anyway (nodes
                # render on top of the connector canvas), and bends need to land on a
                # row that's actually clear of both boxes to render properly.
                (start_x + len(start_label) // 2, start_y + NODE_HEIGHT - 1),
                (end_x + len(end_label) // 2, end_y),
            )

    lines = ["".join(line).rstrip() for line in grid]
    connectors = Text("\n".join(lines), style=COLOR_CONNECTOR)
    nodes = [
        _GraphNode(
            phase_id=entry.phase,
            status=statuses.get(entry.phase, RunStatus.PENDING),
            label=labels[entry.phase][0],
            color=labels[entry.phase][1],
            x=node_positions[entry.phase][0],
            y=node_positions[entry.phase][1],
        )
        for entry in entries
    ]
    return _PipelineLayout(connectors, nodes)


class PhaseNode(Static):
    """Native Textual node for one phase in the execution pipeline graph."""

    can_focus = True
    BINDINGS = [Binding("enter", "select", "Select phase")]

    def __init__(self, phase_id: str, status: RunStatus, label: str) -> None:
        super().__init__(label, classes=f"phase-node status-{status.value}")
        self.phase_id = phase_id
        self.status = status

    def action_select(self) -> None:
        self.post_message(PhaseSelected(self.phase_id))

    def on_click(self) -> None:
        if self.screen.get_selected_text():
            return
        self.action_select()


class PipelineGraph(Widget):
    """Pipeline graph with native phase-node widgets and a connector canvas.

    The DAG is laid out from the origin (see ``_build_pipeline_layout``), then
    re-centered within whatever space this widget is given — otherwise small
    graphs look lost in the top-left corner of a much larger pane.
    """

    def __init__(self, flow: ResolvedFlow, statuses: dict[str, RunStatus], **kwargs: Unpack[WidgetKwargs]) -> None:
        super().__init__(**kwargs)
        self.flow = flow
        self._statuses = dict(statuses)
        self._layout: _PipelineLayout = _PipelineLayout(Text(), [])

    def compose(self) -> Iterator[Widget]:
        self._layout = _build_pipeline_layout(self.flow, self._statuses)

        connectors = Static(self._layout.connectors, id="pipeline-connectors")
        connectors.styles.position = "absolute"
        connectors.styles.layer = "connectors"
        yield connectors

        for node in self._layout.nodes:
            phase_node = PhaseNode(node.phase_id, node.status, node.label)
            phase_node.styles.position = "absolute"
            phase_node.styles.layer = "nodes"
            yield phase_node

        self.call_after_refresh(self._recenter)

    def on_resize(self) -> None:
        self._recenter()

    def _content_size(self) -> tuple[int, int]:
        lines = self._layout.connectors.plain.splitlines()
        width = max((len(line) for line in lines), default=0)
        if self._layout.nodes:
            width = max(width, max(node.x + len(node.label) for node in self._layout.nodes))
            height = max(node.y for node in self._layout.nodes) + 1
        else:
            height = len(lines)
        return width, height

    def _recenter(self) -> None:
        if not self._layout.nodes and not self._layout.connectors.plain:
            return
        content_width, content_height = self._content_size()
        offset_x = max(0, (self.size.width - content_width) // 2)
        offset_y = max(0, (self.size.height - content_height) // 2)

        try:
            self.query_one("#pipeline-connectors", Static).styles.offset = Offset(offset_x, offset_y)
        except NoMatches:
            pass

        nodes_by_id = {node.phase_id: node for node in self._layout.nodes}
        for phase_node in self.query(PhaseNode):
            node = nodes_by_id.get(phase_node.phase_id)
            if node is not None:
                phase_node.styles.offset = Offset(node.x + offset_x, node.y + offset_y)

    def update_statuses(self, statuses: dict[str, RunStatus]) -> None:
        self._statuses = dict(statuses)
        self.refresh(recompose=True, layout=True)
