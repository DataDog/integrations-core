# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""FlowScreen — flow overview, pipeline preview, and launch/resume actions."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Static

from ddev.ai.config.models import AgentConfig, ResolvedFlow
from ddev.cli.meta.ai.tui.screens.base import TogoScreen
from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchInputValues
from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen
from ddev.cli.meta.ai.tui.status import RunStatus
from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected, PipelineGraph


class FlowScreen(TogoScreen):
    """Show resolved flow details and controls for launching or resuming execution."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("l", "launch", "Launch"),
    ]

    def __init__(
        self,
        flow: ResolvedFlow,
        runs_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.flow = flow
        self._runs_dir = runs_dir
        self._togo_title = flow.name or "Flow"

    def compose_body(self) -> Iterator[Widget]:
        with Horizontal(id="flow-body"):
            yield from self._compose_overview()

            graph = PipelineGraph(
                self.flow,
                {entry.phase: RunStatus.PENDING for entry in self.flow.flow},
                id="flow-pipeline",
            )
            graph.border_title = "Pipeline"
            yield graph

        with Horizontal(id="actions"):
            yield Button("Back", id="back")
            yield Button("Launch ▶", id="launch-btn", variant="primary")
            resume_btn = Button("Resume", id="resume", variant="warning")
            resume_btn.display = False
            yield resume_btn

    def _compose_overview(self) -> Iterator[Widget]:
        overview = VerticalScroll(id="flow-overview", classes="panel")
        overview.border_title = "overview"
        with overview:
            if self.flow.description:
                yield Static(self.flow.description, id="flow-description", classes="desc")

            if self.flow.agents:
                yield Static("AGENTS", classes="eyebrow")
                with Vertical(id="flow-agents"):
                    for name, config in self.flow.agents.items():
                        yield from self._compose_agent_summary(name, config)

            if self.flow.inputs:
                yield Static("INPUTS", classes="eyebrow")
                with Vertical(id="flow-inputs"):
                    for flow_input in self.flow.inputs:
                        marker = "required" if flow_input.required else "optional"
                        yield Static(f"○ {flow_input.label} · {marker}", classes="flow-input-row")

    def _compose_agent_summary(self, name: str, config: AgentConfig) -> Iterator[Widget]:
        row = Vertical(classes="flow-agent-row")
        with row:
            yield Static(f"◆ {name} · {config.model or config.provider}", classes="flow-agent-heading")
            if config.tools:
                yield Static(" · ".join(config.tools), classes="flow-agent-tools")

    def on_mount(self) -> None:
        from ddev.cli.meta.ai.tui.runs import ai_runs_dir, has_resumable_run

        runs_dir = self._runs_dir or ai_runs_dir(self.togo_app.ddev_app.repo.path)
        if has_resumable_run(self.flow, runs_dir):
            try:
                self.query_one("#resume").display = True
            except Exception:
                pass

    def on_phase_selected(self, event: PhaseSelected) -> None:
        self.app.push_screen(PhaseConfigScreen(self.flow, event.phase_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "back":
                self.app.pop_screen()
            case "launch-btn":
                self.action_launch()
            case "resume":
                self._do_resume()

    def action_launch(self) -> None:
        from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
        from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

        def _on_dismiss(values: LaunchInputValues | None) -> None:
            if values is not None:
                self.app.push_screen(ExecutionScreen(self.flow, runtime_variables=values, runs_dir=self._runs_dir))

        self.app.push_screen(LaunchModal(self.flow), _on_dismiss)

    def _do_resume(self) -> None:
        from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
        from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

        def _on_dismiss(values: LaunchInputValues | None) -> None:
            if values is not None:
                self.app.push_screen(
                    ExecutionScreen(
                        self.flow,
                        runtime_variables=values,
                        resume=True,
                        runs_dir=self._runs_dir,
                    )
                )

        self.app.push_screen(LaunchModal(self.flow), _on_dismiss)
