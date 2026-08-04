# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum, auto
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ddev.ai.config.models import ResolvedFlow
from ddev.ai.runtime.checkpoints import (
    CancelledCheckpoint,
    CheckpointStatus,
    FailedCheckpoint,
    GoalValidationRecord,
    PhaseCheckpoint,
)
from ddev.ai.runtime.helpers import atomic_write_text


class RunOutcomeReadError(Exception):
    """Raised when a persisted run outcome cannot be read."""


class RunOutcomeError(Exception):
    """Raised when reporting a flow run fails."""


class RunOutcomeBuildError(RunOutcomeError):
    """Raised when the deterministic outcome cannot be built."""


class RunOutcomePersistenceError(RunOutcomeError):
    """Raised when a built outcome cannot be persisted."""


class RunVerdict(StrEnum):
    SUCCEEDED = auto()
    FAILED = auto()
    INCOMPLETE = auto()


class FailureKind(StrEnum):
    NONE = auto()
    PHASE_ERROR = auto()
    GOAL_NOT_MET = auto()
    AGENT_ERROR = auto()
    CONFIG_ERROR = auto()
    TIMEOUT = auto()
    UNKNOWN = auto()


class PhaseReportStatus(StrEnum):
    SUCCEEDED = auto()
    FAILED = auto()
    CANCELLED = auto()
    NOT_RUN = auto()
    SKIPPED_ON_RESUME = auto()


class RunSummaryStatus(StrEnum):
    GENERATING = auto()
    SUCCEEDED = auto()
    UNAVAILABLE = auto()


SUMMARY_ERROR_CHAR_LIMIT = 500
TRUNCATION_MARKER = "\n\n[TRUNCATED: source exceeded the summary context budget]"


def truncate_text(text: str, limit: int) -> str:
    """Truncate ``text`` to ``limit`` characters, appending a marker when cut."""
    if len(text) <= limit:
        return text
    available = max(0, limit - len(TRUNCATION_MARKER))
    return f"{text[:available]}{TRUNCATION_MARKER}"


class RunSummaryMetadata(BaseModel):
    """Metadata for the best-effort LLM narrative attached to a run outcome."""

    model_config = ConfigDict(extra="forbid")

    status: RunSummaryStatus = RunSummaryStatus.UNAVAILABLE
    markdown_path: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None

    @classmethod
    def finished(
        cls,
        *,
        status: RunSummaryStatus,
        started_at: datetime,
        input_tokens: int = 0,
        output_tokens: int = 0,
        markdown_path: str | None = None,
        error: str | None = None,
    ) -> RunSummaryMetadata:
        """Build metadata for a completed (successful or unavailable) summary attempt."""
        finished_at = datetime.now(UTC)
        return cls(
            status=status,
            markdown_path=markdown_path,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_seconds=max(0.0, (finished_at - started_at).total_seconds()),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=truncate_text(error, SUMMARY_ERROR_CHAR_LIMIT) if error is not None else None,
        )


class PhaseReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase_id: str
    status: PhaseReportStatus
    started_at: str | None
    finished_at: str | None
    duration_seconds: float | None
    input_tokens: int
    output_tokens: int
    goal_validations: list[GoalValidationRecord] | None
    error: str | None
    error_type: str | None
    cancellation_reason: str | None = None


class RunOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flow_name: str
    verdict: RunVerdict
    failure_kind: FailureKind
    failed_phase: str | None
    error: str | None
    error_type: str | None
    started_at: str
    finished_at: str
    duration_seconds: float
    phases: list[PhaseReport]
    recorded_input_tokens: int
    recorded_output_tokens: int
    resumed: bool
    skipped_on_resume: list[str]
    run_dir: str
    summary: RunSummaryMetadata = Field(default_factory=RunSummaryMetadata)


GOAL_ERROR_TYPES = frozenset({"GoalAttemptsExhausted", "GoalParseError", "GoalValidationError"})
AGENT_ERROR_TYPES = frozenset({"AgentError", "AgentConnectionError", "AgentRateLimitError", "AgentAPIError"})
CONFIG_ERROR_TYPES = frozenset({"ConfigError", "ResourceUnavailableError"})
CHECKPOINT_REPORT_STATUSES = {
    CheckpointStatus.SUCCESS: PhaseReportStatus.SUCCEEDED,
    CheckpointStatus.FAILED: PhaseReportStatus.FAILED,
    CheckpointStatus.CANCELLED: PhaseReportStatus.CANCELLED,
}


def classify_failure(
    verdict: RunVerdict,
    error_type: str | None,
    failed_phase: str | None,
) -> FailureKind:
    """Classify a deterministic verdict using persisted exception metadata."""
    if verdict is RunVerdict.SUCCEEDED:
        return FailureKind.NONE
    if verdict is RunVerdict.INCOMPLETE:
        return FailureKind.TIMEOUT
    if error_type in GOAL_ERROR_TYPES:
        return FailureKind.GOAL_NOT_MET
    if error_type in AGENT_ERROR_TYPES:
        return FailureKind.AGENT_ERROR
    if error_type in CONFIG_ERROR_TYPES:
        return FailureKind.CONFIG_ERROR
    if failed_phase is not None:
        return FailureKind.PHASE_ERROR
    return FailureKind.UNKNOWN


def build_run_outcome(
    *,
    resolved_flow: ResolvedFlow,
    checkpoints: dict[str, PhaseCheckpoint],
    skipped_on_resume: set[str],
    started_at: datetime,
    finished_at: datetime,
    run_dir: Path,
    resumed: bool,
    exception: BaseException | None,
    failed_phase: str | None,
) -> RunOutcome:
    """Build a run outcome from the flow definition and durable checkpoints."""
    reports = [
        _build_phase_report(entry.phase, checkpoints.get(entry.phase), entry.phase in skipped_on_resume)
        for entry in resolved_flow.flow
    ]
    succeeded = {report.phase_id for report in reports if report.status is PhaseReportStatus.SUCCEEDED}
    skipped = {report.phase_id for report in reports if report.status is PhaseReportStatus.SKIPPED_ON_RESUME}
    failed = [report for report in reports if report.status is PhaseReportStatus.FAILED]
    scheduled = {entry.phase for entry in resolved_flow.flow}

    if failed or exception is not None:
        verdict = RunVerdict.FAILED
    elif succeeded | skipped == scheduled:
        verdict = RunVerdict.SUCCEEDED
    else:
        verdict = RunVerdict.INCOMPLETE

    failed_report = next((report for report in failed if report.phase_id == failed_phase), None)
    if failed_report is None and failed:
        failed_report = failed[0]
    original_exception = _original_exception(exception)
    error: str | None
    error_type: str | None
    resolved_failed_phase: str | None
    if failed_report is not None:
        error = failed_report.error
        error_type = failed_report.error_type
        resolved_failed_phase = failed_report.phase_id
    elif original_exception is not None:
        error = str(original_exception)
        error_type = type(original_exception).__name__
        resolved_failed_phase = failed_phase
    else:
        error = error_type = None
        resolved_failed_phase = failed_phase

    return RunOutcome(
        flow_name=resolved_flow.name,
        verdict=verdict,
        failure_kind=classify_failure(verdict, error_type, resolved_failed_phase),
        failed_phase=resolved_failed_phase,
        error=error,
        error_type=error_type,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_seconds=max(0.0, (finished_at - started_at).total_seconds()),
        phases=reports,
        recorded_input_tokens=sum(report.input_tokens for report in reports),
        recorded_output_tokens=sum(report.output_tokens for report in reports),
        resumed=resumed,
        skipped_on_resume=[entry.phase for entry in resolved_flow.flow if entry.phase in skipped_on_resume],
        run_dir=str(run_dir),
    )


def _build_phase_report(
    phase_id: str,
    checkpoint: PhaseCheckpoint | None,
    skipped_on_resume: bool,
) -> PhaseReport:
    if checkpoint is None:
        return PhaseReport(
            phase_id=phase_id,
            status=PhaseReportStatus.NOT_RUN,
            started_at=None,
            finished_at=None,
            duration_seconds=None,
            input_tokens=0,
            output_tokens=0,
            goal_validations=None,
            error=None,
            error_type=None,
            cancellation_reason=None,
        )

    status = PhaseReportStatus.SKIPPED_ON_RESUME if skipped_on_resume else CHECKPOINT_REPORT_STATUSES[checkpoint.status]
    return PhaseReport(
        phase_id=phase_id,
        status=status,
        started_at=checkpoint.started_at,
        finished_at=checkpoint.finished_at,
        duration_seconds=_duration_seconds(checkpoint.started_at, checkpoint.finished_at),
        input_tokens=checkpoint.tokens.total_input,
        output_tokens=checkpoint.tokens.total_output,
        goal_validations=checkpoint.goal_validations,
        error=checkpoint.error if isinstance(checkpoint, FailedCheckpoint) else None,
        error_type=checkpoint.error_type if isinstance(checkpoint, FailedCheckpoint) else None,
        cancellation_reason=checkpoint.reason if isinstance(checkpoint, CancelledCheckpoint) else None,
    )


def _duration_seconds(started_at: str | None, finished_at: str | None) -> float | None:
    if started_at is None or finished_at is None:
        return None
    try:
        return max(0.0, (datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)).total_seconds())
    except ValueError:
        return None


def _original_exception(exception: BaseException | None) -> BaseException | None:
    if exception is not None and exception.__cause__ is not None:
        return exception.__cause__
    return exception


class RunOutcomeStore:
    """Persist the latest deterministic outcome for a flow run."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, outcome: RunOutcome) -> None:
        atomic_write_text(
            self.path,
            yaml.dump(outcome.model_dump(mode="json"), default_flow_style=False, sort_keys=False),
        )

    def read(self) -> RunOutcome:
        try:
            payload = yaml.safe_load(self.path.read_text(encoding="utf-8"))
            return RunOutcome.model_validate(payload)
        except (OSError, yaml.YAMLError, ValidationError) as e:
            raise RunOutcomeReadError(f"Failed to read run outcome from {self.path}: {e}") from e
