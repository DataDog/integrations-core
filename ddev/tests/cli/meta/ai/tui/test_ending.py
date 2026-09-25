# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.runtime.outcome import (
    FailureKind,
    PhaseReport,
    PhaseReportStatus,
    RunOutcome,
    RunVerdict,
)
from ddev.cli.meta.ai.tui.status import ExecutionStatus, RunStatus

from .conftest import OrchestratorStub, export_screenshot_text


def make_phase(
    phase_id: str,
    status: PhaseReportStatus,
    *,
    error: str | None = None,
    error_type: str | None = None,
) -> PhaseReport:
    return PhaseReport(
        phase_id=phase_id,
        status=status,
        started_at="2026-01-01T00:00:00+00:00" if status is not PhaseReportStatus.NOT_RUN else None,
        finished_at="2026-01-01T00:00:10+00:00" if status is not PhaseReportStatus.NOT_RUN else None,
        duration_seconds=10 if status is not PhaseReportStatus.NOT_RUN else None,
        input_tokens=100 if status is not PhaseReportStatus.NOT_RUN else 0,
        output_tokens=50 if status is not PhaseReportStatus.NOT_RUN else 0,
        goal_validations=None,
        error=error,
        error_type=error_type,
    )


def make_outcome(
    verdict: RunVerdict,
    *,
    phases: list[PhaseReport] | None = None,
    failed_phase: str | None = None,
    error: str | None = None,
    error_type: str | None = None,
) -> RunOutcome:
    phase_reports = phases or [
        make_phase("phase_0", PhaseReportStatus.SUCCEEDED),
        make_phase("phase_1", PhaseReportStatus.SUCCEEDED),
    ]
    return RunOutcome(
        flow_name="Test Flow",
        verdict=verdict,
        failure_kind=(
            FailureKind.NONE
            if verdict is RunVerdict.SUCCEEDED
            else FailureKind.TIMEOUT
            if verdict is RunVerdict.INCOMPLETE
            else FailureKind.PHASE_ERROR
        ),
        failed_phase=failed_phase,
        error=error,
        error_type=error_type,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:20+00:00",
        duration_seconds=20,
        phases=phase_reports,
        recorded_input_tokens=sum(phase.input_tokens for phase in phase_reports),
        recorded_output_tokens=sum(phase.output_tokens for phase in phase_reports),
        resumed=False,
        skipped_on_resume=[],
        run_dir="/tmp/test-run",
    )


async def test_succeeded_ending_screen_renders_verdict_stats_and_phases(make_togo_app):
    from ddev.cli.meta.ai.tui.screens.ending import EndingScreen

    app = make_togo_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = EndingScreen(make_outcome(RunVerdict.SUCCEEDED))
        await app.push_screen(screen)
        await pilot.pause()

        rendered = export_screenshot_text(app)
        stats = screen.query_one("#ending-stats").render().plain

    assert "Flow completed — 2 phases" in rendered
    assert "200 input / 100 output tokens recorded" in stats
    assert "phase_0" in rendered
    assert "phase_1" in rendered


async def test_incomplete_ending_screen_reports_partial_completion(make_togo_app):
    from ddev.cli.meta.ai.tui.screens.ending import EndingScreen

    outcome = make_outcome(
        RunVerdict.INCOMPLETE,
        phases=[
            make_phase("phase_0", PhaseReportStatus.SUCCEEDED),
            make_phase("phase_1", PhaseReportStatus.NOT_RUN),
        ],
    )
    app = make_togo_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(EndingScreen(outcome))
        await pilot.pause()

        rendered = export_screenshot_text(app)

    assert "Flow incomplete — 1 of 2 phases completed" in rendered
    assert "not run" in rendered


async def test_incomplete_ending_screen_shows_cancelled_phase(make_togo_app):
    from ddev.cli.meta.ai.tui.screens.ending import EndingScreen

    outcome = make_outcome(
        RunVerdict.INCOMPLETE,
        phases=[
            make_phase("phase_0", PhaseReportStatus.CANCELLED),
            make_phase("phase_1", PhaseReportStatus.NOT_RUN),
        ],
    )
    app = make_togo_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = EndingScreen(outcome)
        await app.push_screen(screen)
        await pilot.pause()

        rendered = export_screenshot_text(app)
        stats = screen.query_one("#ending-stats").render().plain

    assert "cancelled" in rendered
    assert "1 cancelled" in stats


async def test_failed_ending_screen_renders_error_details(make_togo_app):
    from ddev.cli.meta.ai.tui.screens.ending import EndingScreen

    outcome = make_outcome(
        RunVerdict.FAILED,
        phases=[
            make_phase("phase_0", PhaseReportStatus.SUCCEEDED),
            make_phase(
                "phase_1",
                PhaseReportStatus.FAILED,
                error="goal could not be satisfied",
                error_type="GoalAttemptsExhausted",
            ),
        ],
        failed_phase="phase_1",
        error="goal could not be satisfied",
        error_type="GoalAttemptsExhausted",
    )
    app = make_togo_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = EndingScreen(outcome)
        await app.push_screen(screen)
        await pilot.pause()

        rendered = export_screenshot_text(app)
        error = screen.query_one("#ending-error").render().plain

    assert "Flow failed in phase_1" in rendered
    assert "GoalAttemptsExhausted" in error
    assert "goal could not be satisfied" in error


async def test_execution_screen_offers_summary_without_opening_it_automatically(make_flow, make_togo_app):
    import asyncio

    from textual.containers import Horizontal
    from textual.widgets import Button, Static

    from ddev.cli.meta.ai.tui.screens.ending import EndingScreen
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    release = asyncio.Event()
    outcome = make_outcome(RunVerdict.SUCCEEDED)

    class ControlledOrchestrator(OrchestratorStub):
        failed_phase = None
        outcome: RunOutcome | None = None

        async def run_async(self) -> None:
            await release.wait()
            self.outcome = outcome

    flow = make_flow()
    app = make_togo_app([flow])
    screen = ExecutionScreen(flow, orchestrator_builder=lambda callbacks: ControlledOrchestrator())

    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(screen)
        await pilot.pause()
        assert screen.query_one("#execution-actions", Horizontal).display is False
        assert screen.check_action("show_outcome", ()) is False

        release.set()
        await pilot.pause()

        assert app.screen is screen
        assert app.execution_status is ExecutionStatus.COMPLETED
        assert screen.query_one("#execution-error", Static).display is False
        assert screen.query_one("#execution-actions", Horizontal).display is True
        assert screen.check_action("show_outcome", ()) is True
        assert screen.query_one("#view-summary", Button).has_focus

        await pilot.click("#view-summary")
        await pilot.pause()
        assert isinstance(app.screen, EndingScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is screen

        await pilot.press("s")
        await pilot.pause()
        assert isinstance(app.screen, EndingScreen)


async def test_run_finishing_does_not_interrupt_an_open_phase_log(make_flow, make_togo_app):
    import asyncio

    from textual.containers import Horizontal
    from textual.widgets import Button

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected

    release = asyncio.Event()
    outcome = make_outcome(RunVerdict.SUCCEEDED)

    class ControlledOrchestrator(OrchestratorStub):
        failed_phase = None
        outcome: RunOutcome | None = None

        async def run_async(self) -> None:
            await release.wait()
            self.outcome = outcome

    flow = make_flow()
    app = make_togo_app([flow])
    screen = ExecutionScreen(flow, orchestrator_builder=lambda callbacks: ControlledOrchestrator())

    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(screen)
        await pilot.pause()
        phase_id = flow.flow[0].phase
        screen._phase_statuses[phase_id] = RunStatus.RUNNING
        screen.on_phase_selected(PhaseSelected(phase_id))
        await pilot.pause()
        phase_log = app.screen
        assert isinstance(phase_log, PhaseLogScreen)

        release.set()
        await pilot.pause()

        assert app.screen is phase_log
        assert screen.query_one("#execution-actions", Horizontal).display is True

        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is screen
        assert screen.query_one("#view-summary", Button).has_focus
