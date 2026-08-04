# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Deterministic ending screen shown after a Togo flow run."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from rich.table import Table
from rich.text import Text
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown, Static

from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.runtime.outcome import PhaseReport, PhaseReportStatus, RunOutcome, RunSummaryStatus, RunVerdict
from ddev.cli.meta.ai.tui.screens.base import TogoScreen
from ddev.cli.meta.ai.tui.screens.formatting import compact_error_detail

PHASE_GLYPHS = {
    PhaseReportStatus.SUCCEEDED: "○",
    PhaseReportStatus.FAILED: "✕",
    PhaseReportStatus.CANCELLED: "◌",
    PhaseReportStatus.NOT_RUN: "●",
    PhaseReportStatus.SKIPPED_ON_RESUME: "◌",
}


class EndingScreen(TogoScreen):
    """Show the deterministic result and per-phase accounting for a flow run."""

    BINDINGS = [
        Binding("escape", "back", "Back", priority=True),
        Binding("ctrl+c", "copy_selection", "Copy"),
    ]

    def __init__(self, outcome: RunOutcome) -> None:
        super().__init__()
        self.outcome = outcome
        self._togo_title = f"{outcome.flow_name} · Run outcome"

    def compose_body(self) -> Iterator[Widget]:
        error = Static(self._error_text(), id="ending-error", classes="panel")
        error.display = self.outcome.verdict is RunVerdict.FAILED
        summary = self._summary_widget()
        yield VerticalScroll(
            Static(self._verdict_text(), id="ending-verdict", classes=f"verdict-{self.outcome.verdict.value}"),
            Static(self._stats_text(), id="ending-stats"),
            Static(self._phase_table(), id="ending-phases", classes="panel"),
            error,
            summary,
            id="ending-content",
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_copy_selection(self) -> None:
        self.copy_selection()

    def _verdict_text(self) -> Text:
        completed = sum(
            phase.status in (PhaseReportStatus.SUCCEEDED, PhaseReportStatus.SKIPPED_ON_RESUME)
            for phase in self.outcome.phases
        )
        total = len(self.outcome.phases)
        if self.outcome.verdict is RunVerdict.SUCCEEDED:
            return Text(f"✓ Flow completed — {total} phases")
        if self.outcome.verdict is RunVerdict.FAILED:
            location = f" in {self.outcome.failed_phase}" if self.outcome.failed_phase else ""
            return Text(f"✕ Flow failed{location} — {self.outcome.failure_kind.value.replace('_', ' ')}")
        return Text(f"◌ Flow incomplete — {completed} of {total} phases completed")

    def _stats_text(self) -> Text:
        succeeded = sum(phase.status is PhaseReportStatus.SUCCEEDED for phase in self.outcome.phases)
        failed = sum(phase.status is PhaseReportStatus.FAILED for phase in self.outcome.phases)
        cancelled = sum(phase.status is PhaseReportStatus.CANCELLED for phase in self.outcome.phases)
        return Text(
            f"Duration {_format_duration(self.outcome.duration_seconds)}  ·  "
            f"{succeeded} succeeded  ·  {failed} failed  ·  {cancelled} cancelled  ·  "
            f"{self.outcome.recorded_input_tokens:,} input / "
            f"{self.outcome.recorded_output_tokens:,} output tokens recorded"
        )

    def _phase_table(self) -> Table:
        table = Table(expand=True, box=None, show_header=True, header_style="bold")
        table.add_column("")
        table.add_column("Phase")
        table.add_column("Status")
        table.add_column("Duration", justify="right")
        table.add_column("Tokens (in/out)", justify="right")
        table.add_column("Goal attempts", justify="right")
        for phase in self.outcome.phases:
            table.add_row(
                PHASE_GLYPHS[phase.status],
                phase.phase_id,
                phase.status.value.replace("_", " "),
                _format_duration(phase.duration_seconds),
                f"{phase.input_tokens:,} / {phase.output_tokens:,}",
                _goal_attempts(phase),
            )
        return table

    def _error_text(self) -> Text:
        error_type = self.outcome.error_type or "Unknown error"
        detail = compact_error_detail(self.outcome.error or error_type, self.outcome.failed_phase)
        location = f"Phase: {self.outcome.failed_phase}\n" if self.outcome.failed_phase else ""
        hint = (
            f"\nSelect {self.outcome.failed_phase} on the execution screen for the full log."
            if self.outcome.failed_phase
            else ""
        )
        return Text(f"{location}{error_type}: {detail}{hint}")

    def _summary_widget(self) -> Widget:
        metadata = self.outcome.summary
        if metadata.status is not RunSummaryStatus.SUCCEEDED or metadata.markdown_path is None:
            detail = metadata.error or "No generated narrative is available for this run."
            return Static(f"AI summary unavailable\n\n{detail}", id="ending-summary", classes="panel", markup=False)
        try:
            manager = CheckpointManager.for_run_dir(Path(self.outcome.run_dir))
            path = manager.resolve_run_artifact(metadata.markdown_path)
            markdown = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError) as error:
            return Static(f"AI summary unavailable\n\n{error}", id="ending-summary", classes="panel", markup=False)
        return Markdown(markdown, id="ending-summary", classes="panel")


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remainder = divmod(int(seconds), 60)
    return f"{minutes}m {remainder:02d}s"


def _goal_attempts(phase: PhaseReport) -> str:
    if not phase.goal_validations:
        return "—"
    return str(sum(record.attempts for record in phase.goal_validations))
