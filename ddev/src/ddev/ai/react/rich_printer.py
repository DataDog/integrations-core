# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Rich-based console printer wired as a CallbackSet.

Prints a horizontal rule at the start of each phase, a live spinner while the
agent is awaiting a response, the agent's text replies, and the tool names it
invokes (with a success or failure marker). Every per-agent line is prefixed
with ``[<agent-name>]`` so concurrent phases stay distinguishable.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.status import Status

from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.react.callbacks import CallbackSet
from ddev.ai.tools.core.types import ToolResult


def _prefix(name: str) -> str:
    return f"[bold magenta]\\[{name}][/bold magenta]"


def make_rich_callbacks(console: Console | None = None) -> CallbackSet:
    """Return a CallbackSet that streams ReAct events to the terminal via Rich."""
    out = console or Console()
    cb = CallbackSet()
    state: dict[str, Status | None] = {"status": None}

    def stop_status() -> None:
        active = state["status"]
        if active is not None:
            active.stop()
            state["status"] = None

    @cb.on_phase_start
    async def _on_phase_start(phase_id: str) -> None:
        stop_status()
        out.rule(f"[bold cyan]{phase_id}[/bold cyan]")

    @cb.on_before_agent_send
    async def _on_before_agent_send(iteration: int, name: str) -> None:
        stop_status()
        status = out.status(f"{_prefix(name)} [dim]Thinking…[/dim]", spinner="dots")
        status.start()
        state["status"] = status

    @cb.on_agent_response
    async def _on_agent_response(response: AgentResponse, iteration: int, name: str) -> None:
        stop_status()
        if response.text.strip():
            out.print(_prefix(name))
            out.print(Markdown(response.text))

    @cb.on_tool_call
    async def _on_tool_call(tool_call: ToolCall, result: ToolResult, display: str, iteration: int, name: str) -> None:
        prefix = _prefix(name)
        if result.success:
            out.print(f"{prefix} [cyan]→[/cyan] {display} [green]✓[/green]")
        else:
            error = result.error or "failed"
            out.print(f"{prefix} [cyan]→[/cyan] {display} [red]✗[/red] [dim]{error}[/dim]")

    @cb.on_before_compact
    async def _on_before_compact() -> None:
        stop_status()
        out.print("[yellow]· compacting…[/yellow]")

    @cb.on_error
    async def _on_error(error: BaseException) -> None:
        stop_status()
        out.print(f"[red]✗ {type(error).__name__}: {error}[/red]")

    @cb.on_complete
    async def _on_complete(result) -> None:
        stop_status()

    return cb
