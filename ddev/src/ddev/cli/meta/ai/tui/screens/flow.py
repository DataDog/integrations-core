# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""FlowScreen — flow overview, pipeline preview, and launch/resume actions."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import Button, Static

from ddev.ai.config.models import AgentConfig, ResolvedFlow
from ddev.cli.meta.ai.tui.errors import compact_error_detail
from ddev.cli.meta.ai.tui.screens.base import TogoScreen
from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchInputValues
from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen
from ddev.cli.meta.ai.tui.status import RunStatus
from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected, PipelineGraph

if TYPE_CHECKING:
    from ddev.ai.runtime.checkpoints import ResumeState

PIPELINE_LEGEND = "◇ completed in a previous run · skipped on resume"
CHECKPOINT_UNREADABLE_LEGEND = "✕ checkpoint unreadable · delete it and launch the flow from scratch"


class FlowScreen(TogoScreen):
    """Show resolved flow details and controls for launching or resuming execution."""

    AUTO_FOCUS = "#launch-btn"
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

            with Vertical(id="flow-pipeline-column"):
                graph = PipelineGraph(
                    self.flow,
                    self._preview_statuses(frozenset()),
                    id="flow-pipeline",
                )
                graph.border_title = "Pipeline"
                yield graph

                legend = Static(PIPELINE_LEGEND, id="pipeline-legend", classes="desc")
                legend.display = False
                yield legend

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

    # Textual posts ScreenResume on push as well as pop, so this covers the initial open too.
    def on_screen_resume(self) -> None:
        """Re-read resume state whenever this screen becomes active again."""
        self._apply_resume_state(self._read_resume_state())

    def _preview_statuses(self, completed: frozenset[str]) -> dict[str, RunStatus]:
        """Map the flow's phases to preview statuses, marking dependency-closed successes as checkpointed."""
        return {
            entry.phase: RunStatus.CHECKPOINTED if entry.phase in completed else RunStatus.PENDING
            for entry in self.flow.flow
        }

    def _read_resume_state(self) -> ResumeState:
        from ddev.cli.meta.ai.tui.runs import ai_runs_dir, flow_resume_state

        runs_dir = self._runs_dir or ai_runs_dir(self.togo_app.ddev_app.repo.path)
        return flow_resume_state(self.flow, runs_dir)

    def _apply_resume_state(self, state: ResumeState) -> None:
        """Drive the Resume button, pipeline preview, and legend from a single resume-state read."""
        try:
            self.query_one("#resume", Button).display = state.is_resumable
            self.query_one("#flow-pipeline", PipelineGraph).update_statuses(self._preview_statuses(state.completed))
            self._apply_legend(self.query_one("#pipeline-legend", Static), state)
        except NoMatches:
            pass

    def _apply_legend(self, legend: Static, state: ResumeState) -> None:
        """Explain the checkpointed glyphs, or report a checkpoint file that could not be read."""
        unreadable = state.error is not None
        legend.update(CHECKPOINT_UNREADABLE_LEGEND if unreadable else PIPELINE_LEGEND)
        legend.set_class(unreadable, "legend-error")
        legend.display = unreadable or bool(state.completed)

    def _confirm_resumable(self) -> bool:
        """Re-read the checkpoint before committing to a resume, resyncing the UI if it went stale."""
        state = self._read_resume_state()
        if state.is_resumable:
            return True

        self._apply_resume_state(state)
        if state.error is not None:
            detail = compact_error_detail(state.error).rstrip(".")
            message = f"Cannot resume: {detail}. Delete the checkpoint file and launch from scratch."
        else:
            message = "Nothing left to resume — launch the flow instead."
        self.notify(message, severity="warning", markup=False)
        return False

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

        if not self._confirm_resumable():
            return

        def _on_dismiss(values: LaunchInputValues | None) -> None:
            # The state can go stale while the modal is open, and the dismiss callback runs before
            # the ScreenResume refresh, so re-check rather than commit to a resume that will fail.
            if values is None or not self._confirm_resumable():
                return

            self.app.push_screen(
                ExecutionScreen(
                    self.flow,
                    runtime_variables=values,
                    resume=True,
                    runs_dir=self._runs_dir,
                )
            )

        self.app.push_screen(LaunchModal(self.flow), _on_dismiss)
