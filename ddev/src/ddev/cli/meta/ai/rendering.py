# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pure rendering helpers for AI flow run events.

All functions return ``rich`` renderables (``Text``, ``Panel``, or ``str``)
and have no side-effects: no ``Console``, no ``Application``, no Textual
widgets. The TUI execution view delegates to this module for consistent
visual output across phase logs.
"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING, Any

from rich.markdown import Markdown, TableElement
from rich.panel import Panel
from rich.text import Text

from ddev.ai.agent.exceptions import describe_agent_error
from ddev.ai.agent.scope import AgentRole
from ddev.cli.meta.ai.palette import (
    ERROR,
    ROLE_GOAL_REVIEWER,
    ROLE_PHASE,
    ROLE_SUBAGENT,
    STATUS_DONE,
    STATUS_RUNNING,
    TOOL_CALL,
    TOOL_SEARCH,
)

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderResult

    from ddev.ai.agent.scope import AgentScope
    from ddev.ai.agent.types import ToolCall, WebFetchCall, WebSearchCall
    from ddev.ai.react.types import ReActResult
    from ddev.ai.tools.core.types import ToolResult

# Input field values longer than this are summarized as ``<N chars>`` instead of dumped.
MAX_INLINE_VALUE = 60

# Prompts longer than ``PROMPT_HEAD_CHARS + PROMPT_TAIL_CHARS`` are middle-truncated
# in the console/TUI; the full text is always written verbatim to the JSONL log.
PROMPT_HEAD_CHARS = 1200
PROMPT_TAIL_CHARS = 400
TABLE_MIN_COLUMN_WIDTH = 8

# Per-role visual identity so the reader can tell who is speaking at a glance.
ROLE_STYLES: dict[AgentRole, dict[str, str]] = {
    AgentRole.PHASE: {"label": "agent", "color": ROLE_PHASE, "prompt_border": STATUS_RUNNING},
    AgentRole.SUBAGENT: {"label": "subagent", "color": ROLE_SUBAGENT, "prompt_border": ROLE_SUBAGENT},
    AgentRole.GOAL_REVIEWER: {
        "label": "goal reviewer",
        "color": ROLE_GOAL_REVIEWER,
        "prompt_border": ROLE_GOAL_REVIEWER,
    },
}


def _ellipsize_cell(value: str, width: int) -> str:
    if len(value) <= width:
        return value.ljust(width)
    if width <= 1:
        return "…"[:width]
    return f"{value[: width - 1]}…"


def _table_column_widths(rows: list[list[str]], max_width: int) -> list[int]:
    column_count = len(rows[0])
    separator_width = 3 * (column_count - 1)
    available_width = max(TABLE_MIN_COLUMN_WIDTH * column_count, max_width - separator_width)
    desired_widths = [max(len(row[index]) for row in rows) for index in range(column_count)]
    base_width = max(TABLE_MIN_COLUMN_WIDTH, available_width // column_count)
    widths = [min(width, base_width) for width in desired_widths]

    remaining = available_width - sum(widths)
    while remaining > 0:
        expandable = [index for index, width in enumerate(widths) if width < desired_widths[index]]
        if not expandable:
            break
        for index in expandable:
            if remaining <= 0:
                break
            widths[index] += 1
            remaining -= 1

    return widths


def _format_table_row(row: list[str], widths: list[int]) -> str:
    return " | ".join(_ellipsize_cell(value, width) for value, width in zip(row, widths, strict=True))


def _wrap_table_cell(value: str, width: int) -> list[str]:
    wrapped = textwrap.wrap(
        value,
        width=max(1, width),
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=True,
        drop_whitespace=True,
    )
    return wrapped or [""]


def _format_wrapped_table_row(row: list[str], widths: list[int]) -> list[str]:
    wrapped_cells = [_wrap_table_cell(value, width) for value, width in zip(row, widths, strict=True)]
    row_height = max(len(lines) for lines in wrapped_cells)
    rendered_lines: list[str] = []

    for line_number in range(row_height):
        cells = [
            (lines[line_number] if line_number < len(lines) else "").ljust(width)
            for lines, width in zip(wrapped_cells, widths, strict=True)
        ]
        rendered_lines.append(" | ".join(cells))

    return rendered_lines


class AgentTableElement(TableElement):
    """Markdown table renderer tuned for narrow TUI log panes."""

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        rows: list[list[str]] = []
        if self.header is not None and self.header.row is not None:
            rows.append([cell.content.plain for cell in self.header.row.cells])
        if self.body is not None:
            rows.extend([[cell.content.plain for cell in row.cells] for row in self.body.rows])
        if not rows:
            return

        column_count = max(len(row) for row in rows)
        normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
        widths = _table_column_widths(normalized_rows, options.max_width)

        lines = [_format_wrapped_table_row(normalized_rows[0], widths)[0]]
        lines.append(_format_table_row(["-" * width for width in widths], widths))
        for row in normalized_rows[1:]:
            lines.extend(_format_wrapped_table_row(row, widths))

        yield Text("\n".join(lines), style="markdown.table.border", no_wrap=True, overflow="ellipsis")


class AgentMarkdown(Markdown):
    """Markdown renderable for agent prompts and responses."""

    elements = {**Markdown.elements, "table_open": AgentTableElement}


def _role_style(role: AgentRole) -> dict[str, str]:
    """Return the visual style dict for *role*, defaulting to PHASE."""
    return ROLE_STYLES.get(role, ROLE_STYLES[AgentRole.PHASE])


def _truncate_middle(text: str, head: int, tail: int, log_hint: str) -> str:
    """Keep the start and end of *text*, eliding the middle with a pointer to the full log."""
    if len(text) <= head + tail:
        return text
    omitted = len(text) - head - tail
    return f'{text[:head]}\n\n[... {omitted} chars omitted — full prompt in {log_hint} ...]\n\n{text[-tail:]}'


def _summarize_input(tool_input: dict[str, Any]) -> str:
    """Render a tool call's input as a compact ``k=v`` line, eliding bulky values."""
    parts: list[str] = []
    for key, value in tool_input.items():
        if isinstance(value, str):
            rendered = f"<{len(value)} chars>" if len(value) > MAX_INLINE_VALUE else value
        elif isinstance(value, (list, dict)):
            rendered = f"<{len(value)} items>"
        else:
            rendered = str(value)
        parts.append(f"{key}={rendered}")
    return " ".join(parts)


def _tokens(input_tokens: int, output_tokens: int) -> str:
    """Format a token pair as a compact ``N in / M out`` string."""

    def short(n: int) -> str:
        return f"{n / 1000:.0f}k" if n >= 1000 else str(n)

    return f"{short(input_tokens)} in / {short(output_tokens)} out"


# ---------------------------------------------------------------------------
# Rich renderable builders
# ---------------------------------------------------------------------------


def render_agent_start_header(scope: AgentScope) -> Text:
    """Build the ``▸ <owner_id> [<label>]`` header shown when an agent starts."""
    style = _role_style(scope.role)
    header = Text(f"▸ {scope.owner_id} ", style=f"bold {style['color']}")
    header.append(f"[{style['label']}]", style=f"dim {style['color']}")
    return header


def render_agent_tools_line(tools: list[str]) -> Text:
    """Build the ``tools: t1, t2, …`` line shown below the agent start header."""
    return Text(f"  tools: {', '.join(tools)}", style="dim")


def render_prompt_panel(scope: AgentScope, prompt: str, log_hint: str) -> Panel:
    """Build a ``Panel`` wrapping the (possibly middle-truncated) *prompt*."""
    style = _role_style(scope.role)
    body = _truncate_middle(prompt, PROMPT_HEAD_CHARS, PROMPT_TAIL_CHARS, log_hint)
    title = f"prompt · {style['label']} ({scope.owner_id})"
    return Panel(AgentMarkdown(body), title=title, title_align="left", border_style=style["prompt_border"])


def render_response_header(scope: AgentScope) -> Text:
    """Build the ``◂ response · <label> (<owner_id>)`` header."""
    style = _role_style(scope.role)
    return Text(f"◂ response · {style['label']} ({scope.owner_id})", style=f"bold {style['color']}")


def render_response_text(text: str) -> AgentMarkdown:
    """Render an agent response as Markdown."""
    return AgentMarkdown(text)


def render_tool_call_line(tool_call: ToolCall) -> Text:
    """Build the ``→ <tool> k=v …`` line for a tool call in an agent response."""
    line = Text("  → ", style=TOOL_CALL)
    line.append(tool_call.name, style=f"bold {TOOL_CALL}")
    summary = _summarize_input(tool_call.input)
    if summary:
        line.append(f" {summary}", style="dim")
    return line


def render_web_search_line(search: WebSearchCall) -> Text:
    """Build the ``🔍 web_search <query> (N results)`` line."""
    line = Text("  🔍 ", style=TOOL_SEARCH)
    line.append("web_search", style=f"bold {TOOL_SEARCH}")
    line.append(f" {search.query}", style="dim")
    if search.error:
        line.append(f" — {search.error}", style=ERROR)
    else:
        line.append(f" ({search.result_count} results)", style="dim")
    return line


def render_web_fetch_line(fetch: WebFetchCall) -> Text:
    """Build the ``📄 web_fetch <url> (retrieved …)`` line."""
    line = Text("  📄 ", style=TOOL_SEARCH)
    line.append("web_fetch", style=f"bold {TOOL_SEARCH}")
    line.append(f" {fetch.url}", style="dim")
    if fetch.error:
        line.append(f" — {fetch.error}", style=ERROR)
    elif fetch.retrieved_at:
        line.append(f" (retrieved {fetch.retrieved_at})", style="dim")
    return line


def render_tool_result_line(tool_call: ToolCall, result: ToolResult) -> Text:
    """Build the ``✓/✗ <tool>`` result line shown after a tool call completes."""
    if result.success:
        line = Text("    ✓ ", style=STATUS_DONE)
        line.append(tool_call.name, style="dim")
        if result.truncated:
            line.append(" (truncated)", style="dim")
    else:
        line = Text("    ✗ ", style=ERROR)
        line.append(tool_call.name, style="dim")
        line.append(f" — {result.error}", style=ERROR)
    return line


def render_compact_notice() -> Text:
    """Build the ``⋯ compacting context`` notice line."""
    return Text("  ⋯ compacting context", style="dim")


def render_agent_finish_line(scope: AgentScope, result: ReActResult) -> Text:
    """Build the ``✓ <owner_id> — N iters, X in / Y out`` summary line."""
    return Text(
        f"✓ {scope.owner_id} — {result.iterations} iters, "
        f"{_tokens(result.total_input_tokens, result.total_output_tokens)}",
        style=f"dim {STATUS_DONE}",
    )


def render_agent_error_line(scope: AgentScope, error: BaseException) -> Text:
    """Build the ``✗ <owner_id> — ErrorType: message`` error line."""
    return Text(f"✗ {scope.owner_id} — {describe_agent_error(error)}", style=ERROR)
