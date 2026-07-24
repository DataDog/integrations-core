# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.status import Status
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.junit import TestStatus

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.utils.github_async.models import WorkflowJob
    from ddev.utils.junit import JUnitReport, JUnitTestCase


class Platform(StrEnum):
    """Operating system a test job runs on."""

    LINUX = auto()
    WINDOWS = auto()
    MACOS = auto()


# Characters GitHub disallows in an artifact name (plus CR/LF).
ARTIFACT_NAME_DISALLOWED = re.compile(r'["\:<>|*?\\/\r\n]')
# Separator between the artifact name's fields. Names are matched by reconstruction, not by
# splitting, so the separator does not need to be absent from the field values.
ARTIFACT_NAME_SEPARATOR = "_"


@dataclass
class BatchJob:
    """A single job entry in a TestBatch: one ``target + environment + platform`` execution.

    A ``BatchJob`` is never duplicated into separate unit and E2E rows. Its logical identity is
    ``target + environment + platform``; ``runner_labels`` (one runner selection: the labels a
    single GitHub runner is chosen by) and the ``unit_tests``/``e2e_tests`` facet flags are
    attributes of that identity, describing which test facets the one execution must produce.
    ``environment`` is exactly one resolved Hatch environment, or the empty string for an
    environmentless target.
    """

    name: str
    target: str
    runner_labels: tuple[str, ...]
    environment: str
    platform: Platform
    unit_tests: bool
    e2e_tests: bool

    def artifact_name(self) -> str:
        """Deterministic artifact name built from the job's target, environment, and platform.

        Pure and deterministic. Each field is sanitized to GitHub's artifact-name constraints and
        joined by the separator. Because a job's identity is ``target + environment + platform``,
        those fields are unique per job within a batch and give each job a unique artifact
        identity. An environmentless job contributes no environment segment (so it reads
        ``target_platform`` rather than leaving an empty ``target__platform`` gap); it stays unique
        because such a target produces a single job per platform.
        """
        fields = (self.target, self.environment, str(self.platform))
        return ARTIFACT_NAME_SEPARATOR.join(ARTIFACT_NAME_DISALLOWED.sub("_", field) for field in fields if field)


@dataclass
class JobResult:
    """In-memory result of a single test job (one integration + environment + platform).

    Carries the full parsed JUnit reports for the job, not just its failures, so the PR-comment
    layer can report passed/skipped counts as well.
    """

    integration: str
    environment: str
    platform: Platform
    status: Status
    failed_steps: list[str] = field(default_factory=list)
    reports: tuple[JUnitReport, ...] = ()

    @property
    def failed_tests(self) -> list[JUnitTestCase]:
        """Every failed/errored test case across this job's reports, flattened for rendering."""
        return [
            case
            for report in self.reports
            for suite in report.test_suites
            for case in suite.test_cases
            if case.status in (TestStatus.FAILED, TestStatus.ERROR)
        ]


@dataclass
class BatchJobResult:
    """Everything known about a single job in a finished batch, correlated by the producer.

    ``artifact_name_path`` is the single downloaded folder for the job (named after the job's
    ``artifact_name``); the three ``*_artifact_name`` fields are the expected per-facet file names
    inside that folder.
    """

    job: BatchJob
    workflow_job: WorkflowJob | None
    artifact_name_path: str | None
    unit_artifact_name: str
    e2e_artifact_name: str
    coverage_artifact_name: str

    @staticmethod
    def correlate(
        job_list: list[BatchJob],
        jobs: list[WorkflowJob],
        artifact_dirs: dict[str, Path],
    ) -> list[BatchJobResult]:
        """Correlate each job's spec, its workflow-run result, and its artifact directory.

        The workflow-job join is by name (tolerant of misses). Each job's artifact folder is matched
        by reconstructing its name from the job's fields (``artifact_name``) and looking it up among
        the downloaded folders; the path is recorded only when it exists on disk. That single folder
        holds the three per-facet files, whose names (``unit-``/``e2e-``/``coverage-`` prefixed on
        the base name) are recorded for the gatherer. A job missing from the API or from disk still
        yields a well-formed result.
        """
        jobs_by_name = {job.name: job for job in jobs}

        results: list[BatchJobResult] = []
        for batch_job in job_list:
            base = batch_job.artifact_name()
            artifact_dir = artifact_dirs.get(base)
            artifact_name_path = str(artifact_dir) if artifact_dir is not None and artifact_dir.exists() else None
            results.append(
                BatchJobResult(
                    job=batch_job,
                    workflow_job=jobs_by_name.get(batch_job.name),
                    artifact_name_path=artifact_name_path,
                    unit_artifact_name=f"unit-{base}",
                    e2e_artifact_name=f"e2e-{base}",
                    coverage_artifact_name=f"coverage-{base}",
                )
            )
        return results


@dataclass
class WorkflowStatus:
    """Status of a single GitHub Actions workflow run (one batch), with every job's result.

    ``batch_id`` is the human batch identifier (e.g. ``batch-01``) the comment renders; ``id`` is the
    numeric workflow run id and ``url`` links to the run.
    """

    batch_id: str
    url: str
    id: int
    success_count: int
    failed_count: int
    skipped_count: int
    results: list[JobResult]

    @property
    def status(self) -> Status:
        """Batch-level label: FAILURE if any job failed, else SUCCESS if any passed, else SKIPPED."""
        if self.failed_count > 0:
            return Status.FAILURE
        if self.success_count > 0:
            return Status.SUCCESS
        return Status.SKIPPED


@dataclass
class TestBatch(BaseMessage):
    """Dispatched to trigger a matrix of test jobs.

    ``batch_id`` is the Dispatcher-controlled logical identity (e.g. ``batch-01``) that downstream
    processors correlate on; the inherited ``id`` is the message-instance identity and may differ.
    """

    batch_id: str
    job_list: list[BatchJob]
    jobs_count: int
    integrations: list[str]


@dataclass
class BatchFinished(BaseMessage):
    """Emitted when a GitHub Actions test workflow has completed.

    ``batch_id`` carries the logical batch identity through from the dispatched ``TestBatch`` so the
    gatherer correlates on it rather than on the message ``id``. ``run_id`` is the GitHub Actions
    workflow run id (execution metadata), which is distinct from the logical batch identity.
    """

    batch_id: str
    status: Status
    run_id: int
    workflow_url: str
    artifacts_path: str
    timed_out: bool = False
    batch_jobs: list[BatchJobResult] = field(default_factory=list)


@dataclass
class UpdatePRComment(BaseMessage):
    """Emitted per finished batch to request a PR comment update.

    ``revision`` is the gatherer's monotonic counter (one per consumed ``BatchFinished``); the
    PR-updater renders the latest and rejects stale revisions. ``done`` is ``True`` only on the
    revision that completes the final expected batch.
    """

    revision: int
    done: bool
    workflows: list[WorkflowStatus]

    @property
    def passed(self) -> int:
        return sum(workflow.success_count for workflow in self.workflows)

    @property
    def failed(self) -> int:
        return sum(workflow.failed_count for workflow in self.workflows)

    @property
    def skipped(self) -> int:
        return sum(workflow.skipped_count for workflow in self.workflows)

    @property
    def complete(self) -> int:
        """Total jobs finished so far (passed + failed + skipped across all gathered batches)."""
        return sum(len(workflow.results) for workflow in self.workflows)
