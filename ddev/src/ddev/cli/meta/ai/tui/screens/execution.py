# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""ExecutionScreen — live execution view with a pipeline graph and per-phase drill-down logs."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from textual import events, work
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import Static
from textual.worker import Worker

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import ResolvedFlow
from ddev.ai.react.process import TOOL_RESULTS_SENTINEL
from ddev.cli.meta.ai.rendering import (
    render_agent_error_line,
    render_agent_finish_line,
    render_agent_start_header,
    render_agent_tools_line,
    render_compact_notice,
    render_context_cleared_notice,
    render_phase_error_line,
    render_prompt_panel,
    render_response_header,
    render_response_text,
    render_tool_call_line,
    render_tool_result_line,
    render_web_fetch_line,
    render_web_search_line,
)
from ddev.cli.meta.ai.tui.app import OrchestratorLike
from ddev.cli.meta.ai.tui.messages import (
    AfterGoalCheck,
    AgentBeforeSend,
    AgentErrored,
    AgentFinished,
    AgentResponseReceived,
    AgentStarted,
    AgentToolCalled,
    BeforeCompact,
    BeforeGoalCheck,
    ContextCleared,
    ExecutionFailed,
    ExecutionSucceeded,
    PhaseErrored,
    PhaseFinished,
    PhaseStarted,
    RunErrored,
)
from ddev.cli.meta.ai.tui.runs import ai_runs_dir, flow_slug, resume_completed_phases
from ddev.cli.meta.ai.tui.screens.base import TogoScreen
from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen
from ddev.cli.meta.ai.tui.screens.phase_error_modal import PhaseErrorModal
from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogEntry, PhaseLogScreen
from ddev.cli.meta.ai.tui.status import ExecutionStatus, RunStatus
from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected, PipelineGraph

if TYPE_CHECKING:
    from ddev.ai.runtime.orchestrator import PhaseOrchestrator


type OrchestratorBuilder = Callable[[Callbacks], OrchestratorLike]

BANNER_ERROR_MAX_CHARS = 200


class ExecutionScreen(TogoScreen):
    """Live execution screen: pipeline graph plus per-phase drill-down logs."""

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("ctrl+c", "copy_or_cancel_run", "Copy / Cancel"),
    ]

    def __init__(
        self,
        flow: ResolvedFlow,
        runtime_variables: dict[str, str] | None = None,
        resume: bool = False,
        runs_dir: Path | None = None,
        orchestrator_builder: OrchestratorBuilder | None = None,
    ) -> None:
        super().__init__()
        self.flow = flow
        self.runtime_variables = runtime_variables
        self.resume = resume
        self._runs_dir = runs_dir
        self._orchestrator_builder = orchestrator_builder
        self._togo_title = flow.name or "Execution"

        self._phase_statuses: dict[str, RunStatus] = {entry.phase: RunStatus.PENDING for entry in flow.flow}
        self._task_statuses: dict[tuple[str, str], RunStatus] = {
            (entry.phase, task.name): RunStatus.PENDING
            for entry in flow.flow
            for task in flow.phases[entry.phase].tasks
        }
        self._phase_logs: dict[str, list[PhaseLogEntry]] = {entry.phase: [] for entry in flow.flow}
        self._open_phase_log_screens: dict[str, list[PhaseLogScreen]] = {entry.phase: [] for entry in flow.flow}
        self._active_thinking: dict[str, dict[str, str]] = {entry.phase: {} for entry in flow.flow}
        self._orchestrator: OrchestratorLike | None = None
        self._run_worker: Worker[None] | None = None
        self._phase_errors: dict[str, BaseException] = {}
        # Records every renderable produced by the run — used by tests and to
        # populate phase log screens opened after the fact.
        self._output_renders: list[PhaseLogEntry] = []
        self._output_write_count: int = 0

    def compose_body(self) -> Iterator[Widget]:
        error = Static("", id="execution-error")
        error.display = False
        yield error
        pipeline = PipelineGraph(self.flow, self._phase_statuses, id="pipeline")
        pipeline.border_title = "Pipeline"
        yield pipeline

    def on_mount(self) -> None:
        self.togo_app.bridge_target = self
        if self.resume:
            runs_dir = self._runs_dir or ai_runs_dir(self.togo_app.ddev_app.repo.path)
            for phase_id in resume_completed_phases(self.flow, runs_dir):
                self._phase_statuses[phase_id] = RunStatus.DONE
                for task_phase, task_name in self._task_statuses:
                    if task_phase == phase_id:
                        self._task_statuses[(task_phase, task_name)] = RunStatus.DONE
        self._update_display()
        self.togo_app.execution_status = ExecutionStatus.RUNNING
        self._transition_to_finishing_if_phases_done()
        self._run_worker = self._run_orchestrator()

    def on_unmount(self) -> None:
        self._cancel_run_worker()
        if self.togo_app.bridge_target is self:
            self.togo_app.execution_status = ExecutionStatus.IDLE
            self.togo_app.bridge_target = self.togo_app

    def action_cancel_run(self) -> None:
        """Cancel the running orchestrator worker."""
        self._cancel_run_worker()

    def _cancel_run_worker(self) -> None:
        if self._run_worker is not None:
            self._run_worker.cancel()
        if self.togo_app.bridge_target is self and self.togo_app.execution_status.is_active:
            self.togo_app.execution_status = ExecutionStatus.IDLE

    def action_copy_or_cancel_run(self) -> None:
        if not self.copy_selection():
            self.action_cancel_run()

    def action_back(self) -> None:
        if not self.togo_app.execution_status.is_active:
            self.app.pop_screen()
            return
        from ddev.cli.meta.ai.tui.screens.cancel_run_modal import CancelRunModal

        def on_dismiss(confirmed: bool) -> None:
            if confirmed:
                self.action_cancel_run()
                self.app.pop_screen()

        self.app.push_screen(CancelRunModal(), on_dismiss)

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.action_back()

    @work(exit_on_error=False)
    async def _run_orchestrator(self) -> None:
        from ddev.cli.meta.ai.tui.bridge import build_app_callback_set

        callbacks = Callbacks([build_app_callback_set(self.togo_app)])
        orchestrator: OrchestratorLike | None = None

        try:
            if self._orchestrator_builder is not None:
                orchestrator = self._orchestrator_builder(callbacks)
            else:
                orchestrator = self._build_real_orchestrator(callbacks)
            self._orchestrator = orchestrator
            await orchestrator.run_async()
            self.post_message(ExecutionSucceeded())
        except asyncio.CancelledError:
            if self.togo_app.bridge_target is self:
                self.togo_app.execution_status = ExecutionStatus.IDLE
            raise
        except Exception as error:
            if orchestrator is None or orchestrator.failed_phase is None:
                self.post_message(ExecutionFailed(error))

    def _build_real_orchestrator(self, callbacks: Callbacks) -> PhaseOrchestrator:
        """Construct the real PhaseOrchestrator for production use."""
        from ddev.ai.runtime.orchestrator import PhaseOrchestrator
        from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

        write_root = Path(self.togo_app.ddev_app.repo.path)
        run_root = ai_runs_dir(write_root)
        if not run_root.resolve().is_relative_to(write_root.resolve()):
            raise ValueError(f"Refusing to use AI run directory outside repository: {run_root}")
        run_dir = run_root / flow_slug(self.flow)
        if not self.resume:
            if run_dir.is_symlink():
                run_dir.unlink()
            elif run_dir.exists():
                shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

        return PhaseOrchestrator(
            resolved_flow=self.flow,
            phase_registry=self.togo_app.phase_registry,
            checkpoint_path=run_dir / "checkpoints.yaml",
            runtime_variables=self.runtime_variables or {},
            provider_registry=self.togo_app.provider_registry,
            file_access_policy=FileAccessPolicy(write_root=write_root),
            callbacks=callbacks,
            resume=self.resume,
        )

    # ── Display helpers ──────────────────────────────────────────────────

    def _update_display(self) -> None:
        try:
            self.query_one("#pipeline", PipelineGraph).update_statuses(self._phase_statuses)
        except NoMatches:
            pass

    def _compact_error_detail(self, error: BaseException, phase_id: str | None = None) -> str:
        detail = next((line.strip() for line in str(error).splitlines() if line.strip()), type(error).__name__)
        if phase_id is not None:
            detail = detail.removeprefix(f"Phase '{phase_id}' failed: ")
            detail = detail.removeprefix(f"Phase '{phase_id}': ")
        if len(detail) > BANNER_ERROR_MAX_CHARS:
            detail = f"{detail[: BANNER_ERROR_MAX_CHARS - 1].rstrip()}…"
        return detail

    def _show_error_banner(self, message: str) -> None:
        try:
            widget = self.query_one("#execution-error", Static)
        except NoMatches:
            return
        widget.update(message)
        widget.display = True

    def _show_run_error(self, error: BaseException, phase_id: str | None = None) -> None:
        detail = self._compact_error_detail(error, phase_id)
        title = f"Run failed in {phase_id}" if phase_id is not None else "Run failed"
        hint = f"Select {phase_id} to view the full error." if phase_id is not None else ""
        message = f"{title}: {detail}"
        if hint:
            message = f"{message}\n{hint}"
        self._show_error_banner(message)

    def _show_phase_error_summary(self) -> None:
        ordered_errors = [
            (phase_id, self._phase_errors[phase_id])
            for phase_id in self._phase_statuses
            if phase_id in self._phase_errors
        ]
        if len(ordered_errors) == 1:
            phase_id, error = ordered_errors[0]
            self._show_run_error(error, phase_id)
            return

        lines = [f"Run failed — {len(ordered_errors)} phases failed"]
        lines.extend(f"{phase_id}: {self._compact_error_detail(error, phase_id)}" for phase_id, error in ordered_errors)
        lines.append("Select a failed phase to view its full error.")
        self._show_error_banner("\n".join(lines))

    def _mark_phase_failed(self, phase_id: str) -> None:
        self._phase_statuses[phase_id] = RunStatus.FAILED
        for (task_phase, task_name), status in list(self._task_statuses.items()):
            if task_phase == phase_id and status in (RunStatus.RUNNING, RunStatus.PENDING):
                self._task_statuses[(task_phase, task_name)] = RunStatus.FAILED

    def register_phase_log_screen(self, screen: PhaseLogScreen) -> None:
        self._open_phase_log_screens.setdefault(screen.phase_id, []).append(screen)
        for key, label in self._active_thinking.get(screen.phase_id, {}).items():
            screen.start_thinking(key, label)

    def unregister_phase_log_screen(self, screen: PhaseLogScreen) -> None:
        screens = self._open_phase_log_screens.get(screen.phase_id, [])
        if screen in screens:
            screens.remove(screen)

    def _write_output(self, renderable: PhaseLogEntry, phase_id: str | None = None) -> None:
        """Write a renderable to phase logs and record it for tests."""
        self._output_renders.append(renderable)
        self._output_write_count += 1
        if phase_id is not None:
            self._phase_logs.setdefault(phase_id, []).append(renderable)
            for screen in list(self._open_phase_log_screens.get(phase_id, [])):
                screen.write(renderable)

    def _thinking_key(self, owner_id: str, role: str, iteration: int) -> str:
        return f"{owner_id}:{role}:{iteration}"

    def _start_thinking(self, phase_id: str | None, key: str, label: str) -> None:
        if phase_id is None:
            return
        self._active_thinking.setdefault(phase_id, {})[key] = label
        for screen in list(self._open_phase_log_screens.get(phase_id, [])):
            screen.start_thinking(key, label)

    def _stop_thinking(self, phase_id: str | None, key: str) -> None:
        if phase_id is None:
            return
        self._active_thinking.setdefault(phase_id, {}).pop(key, None)
        for screen in list(self._open_phase_log_screens.get(phase_id, [])):
            screen.stop_thinking(key)

    def _stop_agent_thinking(self, phase_id: str | None, owner_id: str, role: str) -> None:
        if phase_id is None:
            return
        prefix = f"{owner_id}:{role}:"
        for key in list(self._active_thinking.setdefault(phase_id, {})):
            if key.startswith(prefix):
                self._stop_thinking(phase_id, key)

    def _stop_phase_thinking(self, phase_id: str) -> None:
        for key in list(self._active_thinking.setdefault(phase_id, {})):
            self._stop_thinking(phase_id, key)

    # ── Bridge message handlers ──────────────────────────────────────────

    def on_phase_started(self, msg: PhaseStarted) -> None:
        self._phase_statuses[msg.phase_id] = RunStatus.RUNNING
        self._update_display()

    def on_phase_finished(self, msg: PhaseFinished) -> None:
        self._phase_statuses[msg.phase_id] = RunStatus.DONE
        for (p, t), status in list(self._task_statuses.items()):
            if p == msg.phase_id and status in (RunStatus.RUNNING, RunStatus.PENDING):
                self._task_statuses[(p, t)] = RunStatus.DONE
        self._update_display()
        self._transition_to_finishing_if_phases_done()

    def _transition_to_finishing_if_phases_done(self) -> None:
        if self.togo_app.execution_status is ExecutionStatus.RUNNING and all(
            status is RunStatus.DONE for status in self._phase_statuses.values()
        ):
            self.togo_app.execution_status = ExecutionStatus.FINISHING

    def on_execution_succeeded(self, msg: ExecutionSucceeded) -> None:
        self.togo_app.execution_status = ExecutionStatus.COMPLETED

    def on_phase_errored(self, msg: PhaseErrored) -> None:
        self._phase_errors[msg.phase_id] = msg.error
        self._stop_phase_thinking(msg.phase_id)
        self._write_output(render_phase_error_line(msg.phase_id, msg.error), phase_id=msg.phase_id)
        if msg.phase_id in self._phase_statuses:
            self._mark_phase_failed(msg.phase_id)
        self._show_phase_error_summary()
        self._update_display()

    def on_run_errored(self, msg: RunErrored) -> None:
        self.togo_app.execution_status = ExecutionStatus.FAILED
        if self._phase_errors:
            self._show_phase_error_summary()
        else:
            self._show_error_banner("Run failed.")

    def on_execution_failed(self, msg: ExecutionFailed) -> None:
        self.togo_app.execution_status = ExecutionStatus.FAILED
        self._show_run_error(msg.error)

    def on_phase_selected(self, msg: PhaseSelected) -> None:
        status = self._phase_statuses.get(msg.phase_id, RunStatus.PENDING)
        if status is RunStatus.FAILED and (error := self._phase_errors.get(msg.phase_id)) is not None:
            self.app.push_screen(PhaseErrorModal(msg.phase_id, error))
        elif status.has_started:
            self.app.push_screen(PhaseLogScreen(self.flow, msg.phase_id, self._phase_logs[msg.phase_id], source=self))
        else:
            self.app.push_screen(PhaseConfigScreen(self.flow, msg.phase_id))

    def on_agent_started(self, msg: AgentStarted) -> None:
        phase_id = msg.scope.phase_id
        self._write_output(render_agent_start_header(msg.scope), phase_id=phase_id)
        if msg.tools:
            self._write_output(render_agent_tools_line(msg.tools), phase_id=phase_id)

    def on_agent_before_send(self, msg: AgentBeforeSend) -> None:
        phase_id = msg.scope.phase_id
        if msg.prompt != TOOL_RESULTS_SENTINEL:
            self._write_output(render_prompt_panel(msg.scope, msg.prompt, "run artifacts"), phase_id=phase_id)
        key = self._thinking_key(msg.scope.owner_id, msg.scope.role.value, msg.iteration)
        self._start_thinking(phase_id, key, f"{msg.scope.owner_id} · {msg.scope.role.value}")

    def on_agent_response_received(self, msg: AgentResponseReceived) -> None:
        phase_id = msg.scope.phase_id
        key = self._thinking_key(msg.scope.owner_id, msg.scope.role.value, msg.iteration)
        self._stop_thinking(phase_id, key)
        self._write_output(render_response_header(msg.scope), phase_id=phase_id)
        if msg.response.text.strip():
            self._write_output(render_response_text(msg.response.text), phase_id=phase_id)
        for tool_call in msg.response.tool_calls:
            self._write_output(render_tool_call_line(tool_call), phase_id=phase_id)
        for search in msg.response.web_activity.searches:
            self._write_output(render_web_search_line(search), phase_id=phase_id)
        for fetch in msg.response.web_activity.fetches:
            self._write_output(render_web_fetch_line(fetch), phase_id=phase_id)

    def on_agent_tool_called(self, msg: AgentToolCalled) -> None:
        self._write_output(render_tool_result_line(msg.tool_call, msg.result), phase_id=msg.scope.phase_id)

    def on_before_compact(self, msg: BeforeCompact) -> None:
        self._write_output(render_compact_notice(), phase_id=msg.scope.phase_id)

    def on_context_cleared(self, msg: ContextCleared) -> None:
        self._write_output(render_context_cleared_notice(), phase_id=msg.scope.phase_id)

    def on_agent_finished(self, msg: AgentFinished) -> None:
        phase_id = msg.scope.phase_id
        self._stop_agent_thinking(phase_id, msg.scope.owner_id, msg.scope.role.value)
        self._write_output(render_agent_finish_line(msg.scope, msg.result), phase_id=phase_id)

    def on_agent_errored(self, msg: AgentErrored) -> None:
        phase_id = msg.scope.phase_id
        self._stop_agent_thinking(phase_id, msg.scope.owner_id, msg.scope.role.value)
        self._write_output(render_agent_error_line(msg.scope, msg.error), phase_id=phase_id)
        if phase_id is not None:
            self._mark_phase_failed(phase_id)
        self._update_display()

    def on_before_goal_check(self, msg: BeforeGoalCheck) -> None:
        key = (msg.phase_id, msg.task_name)
        if key in self._task_statuses:
            self._task_statuses[key] = RunStatus.RUNNING
            self._update_display()

    def on_after_goal_check(self, msg: AfterGoalCheck) -> None:
        key = (msg.phase_id, msg.task_name)
        if key in self._task_statuses:
            self._task_statuses[key] = RunStatus.DONE if msg.valid else RunStatus.FAILED
            self._update_display()
