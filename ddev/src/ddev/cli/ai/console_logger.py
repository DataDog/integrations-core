# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pretty terminal renderer for AI flow runs.

Wires a ``CallbackSet`` onto the orchestrator that renders the agent
conversation — prompts, responses, tool calls, goal checks — as readable
terminal output instead of the raw JSONL the ``AgentLogger`` writes to disk.
The JSONL file stays on disk untouched; this is purely a console view.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rich.panel import Panel
from rich.text import Text

from ddev.ai.agent.scope import AgentRole
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.agent.scope import AgentScope
    from ddev.ai.agent.types import AgentResponse, ToolCall
    from ddev.ai.react.types import ReActResult
    from ddev.ai.tools.core.types import ToolResult
    from ddev.cli.application import Application

# The HTTP client libraries log every request at INFO ("HTTP Request: POST ... 200 OK"),
# which floods the console view. Raise their threshold so only warnings and above show.
HTTP_LOGGERS = ("httpx", "httpcore", "http.client", "anthropic", "urllib3")

# The before_agent_send hook fires this sentinel when the agent is being fed tool
# results rather than a fresh prompt — there is nothing human-readable to show.
TOOL_RESULTS_SENTINEL = "Tool results"

# Input field values longer than this are summarized as ``<N chars>`` instead of dumped.
MAX_INLINE_VALUE = 60

# Prompts longer than ``PROMPT_HEAD_CHARS + PROMPT_TAIL_CHARS`` are middle-truncated on the
# console; the full text is always written verbatim to the run's JSONL under .ddev/ai-runs/.
PROMPT_HEAD_CHARS = 1200
PROMPT_TAIL_CHARS = 400


# Per-role visual identity so the reader can tell who is speaking at a glance: the main
# phase agent, a spawned subagent, or the goal reviewer that grades each attempt.
ROLE_STYLES: dict[AgentRole, dict[str, str]] = {
    AgentRole.PHASE: {"label": "agent", "color": "cyan", "prompt_border": "blue"},
    AgentRole.SUBAGENT: {"label": "subagent", "color": "yellow", "prompt_border": "yellow"},
    AgentRole.GOAL_REVIEWER: {"label": "goal reviewer", "color": "magenta", "prompt_border": "magenta"},
}


def _role_style(role: AgentRole) -> dict[str, str]:
    return ROLE_STYLES.get(role, ROLE_STYLES[AgentRole.PHASE])


def _truncate_middle(text: str, head: int, tail: int, log_hint: str) -> str:
    """Keep the start and end of ``text``, eliding the middle with a pointer to the full log."""
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
    def short(n: int) -> str:
        return f"{n / 1000:.0f}k" if n >= 1000 else str(n)

    return f"{short(input_tokens)} in / {short(output_tokens)} out"


def build_console_callbacks(app: Application, *, verbose: bool, run_dir: Path) -> Callbacks:
    """Build the pretty-printing callbacks.

    Phase-level events always render. The full agent conversation (prompts,
    responses, tool calls) renders only when ``verbose`` is set. ``run_dir`` is
    the run's artifact directory, referenced when a long prompt is truncated.
    """
    console = app.console
    log_hint = str(run_dir)
    cb = CallbackSet()

    for logger_name in HTTP_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Owner ids that just received a fresh prompt and are awaiting their first response,
    # so the role header is printed once per prompt rather than before every response.
    pending_response_header: set[str] = set()

    @cb.on_phase_start
    async def _on_phase_start(phase_id: str) -> None:
        app.display_header(f"Phase: {phase_id}")

    @cb.on_phase_finish
    async def _on_phase_finish(phase_id: str) -> None:
        app.display_success(f"✓ Phase '{phase_id}' complete")

    @cb.on_after_goal_check
    async def _on_after_goal_check(task_name: str, attempt: int, valid: bool, reason: str) -> None:
        if valid:
            app.display_success(f"  ✓ goal met: {task_name} (attempt {attempt})")
        else:
            app.display_warning(f"  ✗ goal not met: {task_name} (attempt {attempt}) — {reason}")

    if not verbose:
        return Callbacks([cb])

    @cb.on_agent_start
    async def _on_agent_start(scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
        style = _role_style(scope.role)
        header = Text(f"▸ {scope.owner_id} ", style=f"bold {style['color']}")
        header.append(f"[{style['label']}]", style=f"dim {style['color']}")
        console.print(header)
        if tools:
            console.print(Text(f"  tools: {', '.join(tools)}", style="dim"))

    @cb.on_before_agent_send
    async def _on_before_agent_send(scope: AgentScope, prompt: str, iteration: int) -> None:
        if prompt == TOOL_RESULTS_SENTINEL:
            return
        style = _role_style(scope.role)
        body = _truncate_middle(prompt, PROMPT_HEAD_CHARS, PROMPT_TAIL_CHARS, log_hint)
        title = f"prompt · {style['label']} ({scope.owner_id})"
        console.print(Panel(body, title=title, title_align="left", border_style=style["prompt_border"]))
        pending_response_header.add(scope.owner_id)

    @cb.on_agent_response
    async def _on_agent_response(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        style = _role_style(scope.role)
        if scope.owner_id in pending_response_header:
            pending_response_header.discard(scope.owner_id)
            header = Text(f"◂ response · {style['label']} ({scope.owner_id})", style=f"bold {style['color']}")
            console.print(header)
        if response.text.strip():
            console.print(Text(response.text, style="default"))
        for tool_call in response.tool_calls:
            line = Text("  → ", style="yellow")
            line.append(tool_call.name, style="bold yellow")
            summary = _summarize_input(tool_call.input)
            if summary:
                line.append(f" {summary}", style="dim")
            console.print(line)
        for search in response.web_activity.searches:
            line = Text("  🔍 ", style="magenta")
            line.append("web_search", style="bold magenta")
            line.append(f" {search.query}", style="dim")
            if search.error:
                line.append(f" — {search.error}", style="red")
            else:
                line.append(f" ({search.result_count} results)", style="dim")
            console.print(line)
        for fetch in response.web_activity.fetches:
            line = Text("  📄 ", style="magenta")
            line.append("web_fetch", style="bold magenta")
            line.append(f" {fetch.url}", style="dim")
            if fetch.error:
                line.append(f" — {fetch.error}", style="red")
            elif fetch.retrieved_at:
                line.append(f" (retrieved {fetch.retrieved_at})", style="dim")
            console.print(line)

    @cb.on_tool_call
    async def _on_tool_call(scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        if result.success:
            line = Text("    ✓ ", style="green")
            line.append(tool_call.name, style="dim")
            if result.truncated:
                line.append(" (truncated)", style="dim")
        else:
            line = Text("    ✗ ", style="red")
            line.append(tool_call.name, style="dim")
            line.append(f" — {result.error}", style="red")
        console.print(line)

    @cb.on_before_compact
    async def _on_before_compact(scope: AgentScope) -> None:
        console.print(Text("  ⋯ compacting context", style="dim"))

    @cb.on_agent_finish
    async def _on_agent_finish(scope: AgentScope, result: ReActResult) -> None:
        console.print(
            Text(
                f"✓ {scope.owner_id} — {result.iterations} iters, "
                f"{_tokens(result.total_input_tokens, result.total_output_tokens)}",
                style="dim green",
            )
        )

    @cb.on_agent_error
    async def _on_agent_error(scope: AgentScope, error: BaseException) -> None:
        console.print(Text(f"✗ {scope.owner_id} — {type(error).__name__}: {error}", style="red"))

    return Callbacks([cb])
