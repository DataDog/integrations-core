# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.status import Status
from ddev.event_bus.orchestrator import BaseMessage
from ddev.utils.junit import TestStatus
from ddev.utils.platform import PlatformName

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.cli.ci.tests.progress import DispatcherProgress
    from ddev.utils.github_async.models import WorkflowJob
    from ddev.utils.junit import JUnitReport, JUnitTestCase


# Characters GitHub disallows in an artifact name (plus CR/LF).
ARTIFACT_NAME_DISALLOWED = re.compile(r'["\:<>|*?\\/\r\n]')
# Separator between the artifact name's fields. Names are matched by reconstruction, not by
# splitting, so the separator does not need to be absent from the field values.
ARTIFACT_NAME_SEPARATOR = "_"
MINIMUM_BASE_PACKAGE_PREFIX = "minimum-base-package-"


@dataclass(frozen=True)
class BatchJob:
    """One execution of a target, in one environment, on one platform.

    A job is never duplicated into separate unit and E2E rows; the facet flags say which kinds of
    tests the single execution produces. Frozen so jobs are hashable and a batch partition can be
    validated by value.
    """

    name: str
    target: str
    runner_labels: tuple[str, ...]
    environment: str  # empty for a target that defines no environments
    platform: PlatformName
    python_version: str  # `major.minor`, set up on the runner
    unit_tests: bool
    e2e_tests: bool
    agent_image: str | None = None  # `None` when the job runs no E2E tests
    # Runs against the oldest supported `datadog-checks-base` rather than the current one.
    minimum_base_package: bool = False
    coverage: bool = True  # `False` for a job that runs without `--cov`

    def artifact_name(self) -> str:
        """Sanitized, deterministic name built from the job's identity.

        Identity is target, environment, platform and the base package variant, so the name is unique
        within a batch. An environmentless job contributes no segment rather than an empty one.
        """
        fields = (self.target, self.environment, self.platform)
        name = ARTIFACT_NAME_SEPARATOR.join(ARTIFACT_NAME_DISALLOWED.sub("_", field) for field in fields if field)
        return f"{MINIMUM_BASE_PACKAGE_PREFIX}{name}" if self.minimum_base_package else name


@dataclass
class JobResult:
    """In-memory result of a single test job (one integration + environment + platform).

    Carries the full parsed JUnit reports for the job, not just its failures, so the PR-comment
    layer can report passed/skipped counts as well.
    """

    integration: str
    environment: str
    platform: PlatformName
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

    `artifact_name_path` is the single downloaded folder for the job (named after the job's
    `artifact_name`); the three `*_artifact_name` fields are the expected per-facet file names
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
        by reconstructing its name from the job's fields (`artifact_name`) and looking it up among
        the downloaded folders; the path is recorded only when it exists on disk. That single folder
        holds the three per-facet files, whose names (`unit-`/`e2e-`/`coverage-` prefixed on
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

    `batch_id` is the human batch identifier (e.g. `batch-01`) the comment renders; `id` is the
    numeric workflow run id and `url` links to the run.
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

    The `batch_id` is the logical batch identity (e.g. `batch-01`): assigned during planning, stable
    across workflow attempts, and distinct from `BaseMessage.id`, which identifies one message.
    """

    # Logical batch identity (`batch-01`) that downstream processors correlate on. Distinct from
    # the inherited message `id`, which identifies the message instance.
    batch_id: str
    job_list: list[BatchJob]
    jobs_count: int
    integrations: list[str]


@dataclass
class BatchFinished(BaseMessage):
    """Emitted when a GitHub Actions test workflow has completed.

    ``batch_id`` is the identity of the ``TestBatch`` this run came from, so the gatherer can resolve
    it in the plan.
    """

    batch_id: str
    status: Status
    run_id: int  # GitHub Actions workflow run
    workflow_url: str
    artifacts_path: str
    timed_out: bool = False
    batch_jobs: list[BatchJobResult] = field(default_factory=list)


@dataclass
class UpdatePRComment(BaseMessage):
    """Emitted per finished batch to request a PR comment update.

    ``revision`` is ordering metadata: revision ``0`` is the initial plan, then one per consumed
    ``BatchFinished``. The run reporter renders the latest and rejects stale revisions. ``progress`` is
    the whole payload, including whether the run is done and every count the comment needs.
    """

    revision: int
    progress: DispatcherProgress
