# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""TogoApp — themed shell for the Togo AI harness."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from textual import events, on, work
from textual.app import App
from textual.binding import Binding
from textual.message_pump import MessagePump
from textual.reactive import reactive

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.phases.registry import PhaseRegistry
from ddev.cli.meta.ai.palette import STATUS_DONE, STATUS_FAILED, STATUS_PENDING, STATUS_RUNNING
from ddev.cli.meta.ai.tui.messages import NoticeMessage
from ddev.cli.meta.ai.tui.status import ExecutionStatus
from ddev.cli.meta.ai.tui.theme import togo_markdown_theme, togo_theme

if TYPE_CHECKING:
    from ddev.ai.config.engine import ConfigurationEngine
    from ddev.cli.application import Application


class OrchestratorLike(Protocol):
    """Object that can be run by the TUI shell."""

    @property
    def failed_phase(self) -> str | None: ...

    async def run_async(self) -> None: ...


class TogoApp(App):
    """Textual application shell for the Togo AI harness.

    Registers and activates the ``togo`` theme on mount.  Exposes:

    - ``engine``: the configuration engine whose validated flow results are displayed.
    - ``execution_status``: the app-wide reactive lifecycle of the active flow.
    - ``bridge_target``: the MessagePump that the event bridge posts to.
      Defaults to the app itself; later phases can swap in a screen.
    - ``run_flow(orchestrator)``: async worker that awaits
      ``orchestrator.run_async()``.
    - ``received``: list of every bridge message received — used as a test
      sink.
    """

    CSS_PATH = str(Path(__file__).parent / "togo.tcss")
    ENABLE_COMMAND_PALETTE = False

    execution_status: reactive[ExecutionStatus] = reactive(ExecutionStatus.IDLE)

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(
        self,
        *,
        engine: ConfigurationEngine,
        phase_registry: PhaseRegistry,
        provider_registry: AgentProviderRegistry,
        ddev_app: Application,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.phase_registry = phase_registry
        self.provider_registry = provider_registry
        self.received: list[NoticeMessage] = []
        self.bridge_target: MessagePump = self
        self.ddev_app: Application = ddev_app
        self.console.push_theme(togo_markdown_theme)

    def get_theme_variable_defaults(self) -> dict[str, str]:
        """Provide parse-time defaults for status variables so $status-* resolves in CSS."""
        return {
            "status-running": STATUS_RUNNING,
            "status-pending": STATUS_PENDING,
            "status-done": STATUS_DONE,
            "status-failed": STATUS_FAILED,
        }

    def on_mount(self) -> None:
        from ddev.cli.meta.ai.tui.screens.main import MainScreen

        self.register_theme(togo_theme)
        self.theme = "togo"
        self.push_screen(MainScreen())

    def copy_to_clipboard(self, text: str) -> None:
        """Copy through system APIs when available and always fall back to OSC 52."""
        try:
            import pyperclip

            pyperclip.copy(text)
        except Exception:
            if sys.platform == "darwin":
                try:
                    subprocess.run(["/usr/bin/pbcopy"], input=text, text=True, check=True)
                except Exception:
                    pass
        try:
            super().copy_to_clipboard(text)
        except Exception:
            pass

    @on(events.TextSelected)
    def on_text_selected(self) -> None:
        selection = self.screen.get_selected_text()
        if selection:
            self.copy_to_clipboard(selection)

    @work
    async def run_flow(self, orchestrator: OrchestratorLike) -> None:
        """Run the orchestrator on the app's event loop."""
        await orchestrator.run_async()

    def on_notice_message(self, message: NoticeMessage) -> None:
        self.received.append(message)
