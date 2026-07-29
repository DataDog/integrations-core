# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import FlowEntry, ResolvedFlow
from ddev.ai.runtime.outcome import (
    FailureKind,
    PhaseReportStatus,
    RunOutcomeStore,
    RunVerdict,
    build_run_outcome,
    classify_failure,
)

from .helpers import make_cancelled_checkpoint, make_failed_checkpoint, make_success_checkpoint


def make_flow() -> ResolvedFlow:
    return ResolvedFlow(
        name="demo",
        description="Demo flow",
        inputs=[],
        agents={},
        phases={},
        flow=[
            FlowEntry(phase="inspect"),
            FlowEntry(phase="write", dependencies=["inspect"]),
        ],
        variables={},
    )


def build_outcome(
    tmp_path: Path,
    *,
    checkpoints=None,
    exception: BaseException | None = None,
    failed_phase: str | None = None,
    skipped_on_resume: set[str] | None = None,
):
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    return build_run_outcome(
        resolved_flow=make_flow(),
        checkpoints=checkpoints or {},
        skipped_on_resume=skipped_on_resume or set(),
        started_at=started_at,
        finished_at=started_at + timedelta(seconds=75),
        run_dir=tmp_path,
        resumed=bool(skipped_on_resume),
        exception=exception,
        failed_phase=failed_phase,
    )


def test_all_successful_checkpoints_produce_succeeded_outcome(tmp_path: Path):
    outcome = build_outcome(
        tmp_path,
        checkpoints={
            "inspect": make_success_checkpoint(),
            "write": make_success_checkpoint(),
        },
    )

    assert outcome.verdict is RunVerdict.SUCCEEDED
    assert outcome.failure_kind is FailureKind.NONE
    assert outcome.recorded_input_tokens == 20
    assert outcome.recorded_output_tokens == 40
    assert outcome.duration_seconds == 75


def test_missing_success_checkpoint_produces_incomplete_timeout_outcome(tmp_path: Path):
    outcome = build_outcome(
        tmp_path,
        checkpoints={"inspect": make_success_checkpoint()},
    )

    assert outcome.verdict is RunVerdict.INCOMPLETE
    assert outcome.failure_kind is FailureKind.TIMEOUT
    assert [phase.status for phase in outcome.phases] == [
        PhaseReportStatus.SUCCEEDED,
        PhaseReportStatus.NOT_RUN,
    ]


def test_cancelled_checkpoint_produces_cancelled_incomplete_outcome(tmp_path: Path):
    outcome = build_outcome(
        tmp_path,
        checkpoints={
            "inspect": make_cancelled_checkpoint(reason="Orchestrator exceeded max_timeout of 1.0s"),
        },
    )

    assert outcome.verdict is RunVerdict.INCOMPLETE
    assert outcome.failure_kind is FailureKind.TIMEOUT
    assert [phase.status for phase in outcome.phases] == [
        PhaseReportStatus.CANCELLED,
        PhaseReportStatus.NOT_RUN,
    ]
    assert outcome.phases[0].cancellation_reason == "Orchestrator exceeded max_timeout of 1.0s"
    assert outcome.phases[0].error is None


def test_failed_checkpoint_produces_failed_outcome_with_original_error_type(tmp_path: Path):
    outcome = build_outcome(
        tmp_path,
        checkpoints={
            "inspect": make_success_checkpoint(),
            "write": make_failed_checkpoint(error="goal failed", error_type="GoalAttemptsExhausted"),
        },
        exception=RuntimeError("wrapped run failure"),
        failed_phase="write",
    )

    assert outcome.verdict is RunVerdict.FAILED
    assert outcome.failure_kind is FailureKind.GOAL_NOT_MET
    assert outcome.failed_phase == "write"
    assert outcome.error == "goal failed"
    assert outcome.error_type == "GoalAttemptsExhausted"


def test_resume_skipped_phase_counts_as_successful_completion(tmp_path: Path):
    outcome = build_outcome(
        tmp_path,
        checkpoints={
            "inspect": make_success_checkpoint(),
            "write": make_success_checkpoint(),
        },
        skipped_on_resume={"inspect"},
    )

    assert outcome.verdict is RunVerdict.SUCCEEDED
    assert outcome.phases[0].status is PhaseReportStatus.SKIPPED_ON_RESUME
    assert outcome.skipped_on_resume == ["inspect"]
    assert outcome.resumed is True


def test_wrapped_startup_failure_uses_original_exception(tmp_path: Path):
    wrapper = RuntimeError("orchestration failed")
    wrapper.__cause__ = ConfigError("invalid flow input")

    outcome = build_outcome(tmp_path, exception=wrapper)

    assert outcome.verdict is RunVerdict.FAILED
    assert outcome.failure_kind is FailureKind.CONFIG_ERROR
    assert outcome.error == "invalid flow input"
    assert outcome.error_type == "ConfigError"


@pytest.mark.parametrize(
    "error_type, expected",
    [
        pytest.param("GoalValidationError", FailureKind.GOAL_NOT_MET, id="goal"),
        pytest.param("AgentAPIError", FailureKind.AGENT_ERROR, id="agent"),
        pytest.param("ConfigError", FailureKind.CONFIG_ERROR, id="config"),
        pytest.param("UnexpectedError", FailureKind.PHASE_ERROR, id="phase"),
    ],
)
def test_classify_failure(error_type: str, expected: FailureKind):
    assert classify_failure(RunVerdict.FAILED, error_type, "phase") is expected


def test_run_outcome_store_round_trips_and_overwrites(tmp_path: Path):
    store = RunOutcomeStore(tmp_path)
    first = build_outcome(tmp_path, checkpoints={"inspect": make_success_checkpoint()})
    second = build_outcome(
        tmp_path,
        checkpoints={
            "inspect": make_success_checkpoint(),
            "write": make_success_checkpoint(),
        },
    )

    store.write(first)
    store.write(second)

    assert store.read() == second
