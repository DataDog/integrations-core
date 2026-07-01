# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, BatchJobResult, TestBatch, split_artifact_name
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import WorkflowJob, WorkflowRun


def _conclusion_to_status(conclusion: str | None) -> Literal["success", "failure", "skipped"]:
    """Map a GitHub Actions conclusion string to a BatchFinished status.

    Note: ``None`` maps to ``"failure"`` here while the check run reports ``"neutral"``
    for the same input. The asymmetry is intentional — BatchFinished consumers want a
    binary outcome, the check UI prefers an explicit ``"neutral"`` badge.
    """
    if conclusion == "success":
        return "success"
    if conclusion == "skipped":
        return "skipped"
    return "failure"


@dataclass(frozen=True)
class TestRunnerOptions:
    """Configuration for a ``TaskTestRunner``."""

    owner: str
    repo: str
    workflow_id: str | int
    ref: str
    base_sha: str
    checkout_sha: str
    artifacts_base_path: Path
    poll_interval_seconds: float = 30.0


class TaskTestRunner(AsyncProcessor[TestBatch]):
    """
    Runs one ``test-batch.yaml`` workflow for a ``TestBatch``: dispatches the run,
    opens a check run, polls until the workflow completes, downloads its artifacts,
    and emits a ``BatchFinished``.
    """

    def __init__(self, name: str, client: AsyncGitHubClient, options: TestRunnerOptions) -> None:
        super().__init__(name)
        self._client = client
        self._options = options
        self._logger = logging.getLogger(f"{__name__}.{name}")

    async def process_message(self, message: TestBatch) -> None:
        inputs = self._build_inputs(message)
        log_extra: dict[str, Any] = {"batch_id": message.id}

        dispatch = await self._client.create_workflow_dispatch(
            self._options.owner, self._options.repo, self._options.workflow_id, ref=self._options.ref, inputs=inputs
        )
        run_id = dispatch.data.workflow_run_id
        log_extra["run_id"] = run_id
        self._logger.info("Dispatched batch", extra=log_extra)

        run = await self._client.get_workflow_run(self._options.owner, self._options.repo, run_id)
        workflow_url = run.data.html_url
        log_extra["workflow_url"] = workflow_url

        check = await self._client.create_check_run(
            self._options.owner,
            self._options.repo,
            name=f"test-batch/{message.id}",
            head_sha=self._options.base_sha,
            status="in_progress",
            details_url=workflow_url,
        )
        check_run_id = check.data.id
        log_extra["check_run_id"] = check_run_id
        self._logger.info("Check run created", extra=log_extra)

        final_conclusion: str = "cancelled"
        finished: BatchFinished | None = None
        try:
            if run.data.status != "completed":
                run = await self._poll_until_complete(run_id, log_extra)
            else:
                self._logger.info("Workflow completed", extra=log_extra)

            raw = run.data.conclusion
            if raw is None:
                self._logger.warning("Workflow completed with null conclusion", extra=log_extra)
            final_conclusion = raw or "neutral"

            artifacts_path, artifact_dirs = await self._download_artifacts(run_id, log_extra)
            self._logger.info("Artifacts downloaded", extra=log_extra)

            jobs = await self._list_jobs(run_id, log_extra)
            batch_jobs = self._build_batch_jobs(message.job_list, jobs, artifact_dirs)

            finished = BatchFinished(
                id=message.id,
                status=_conclusion_to_status(raw),
                run_id=run_id,
                workflow_url=workflow_url,
                artifacts_path=str(artifacts_path),
                batch_jobs=batch_jobs,
            )
        finally:
            try:
                await self._client.update_check_run(
                    self._options.owner,
                    self._options.repo,
                    check_run_id,
                    status="completed",
                    conclusion=final_conclusion,
                    details_url=workflow_url,
                )
                self._logger.info("Check run closed", extra={**log_extra, "conclusion": final_conclusion})
            except Exception:
                self._logger.exception("Failed to close check run", extra={**log_extra, "conclusion": final_conclusion})

        if finished is not None:
            self.submit_message(finished)
            self._logger.info("BatchFinished emitted", extra=log_extra)

    async def _poll_until_complete(self, run_id: int, log_extra: dict[str, Any]) -> GitHubResponse[WorkflowRun]:
        while True:
            await asyncio.sleep(self._options.poll_interval_seconds)
            run = await self._client.get_workflow_run(self._options.owner, self._options.repo, run_id)
            if run.data.status == "completed":
                self._logger.info("Workflow completed", extra=log_extra)
                return run

    async def _list_jobs(self, run_id: int, log_extra: dict[str, Any]) -> list[WorkflowJob]:
        """Fetch the workflow run's jobs; on failure log a warning and return an empty list."""
        jobs: list[WorkflowJob] = []
        try:
            async for page in self._client.list_workflow_jobs(self._options.owner, self._options.repo, run_id):
                jobs.extend(page.data.jobs)
        except Exception:
            self._logger.warning("Failed to list workflow jobs", extra=log_extra, exc_info=True)
        return jobs

    @staticmethod
    def _build_batch_jobs(
        job_list: list[BatchJob], jobs: list[WorkflowJob], artifact_dirs: dict[str, Path]
    ) -> list[BatchJobResult]:
        """Correlate each job's spec, its workflow-run result, and its artifact directory.

        The workflow-job join is by name (tolerant of misses). Each downloaded artifact folder is
        identified by reversing its name into ``(target, environment, platform)``, which is matched
        to the batch job. That single folder holds the three per-facet files, whose names
        (``unit-``/``e2e-``/``coverage-`` prefixed on the base name) are recorded for the gatherer.
        A job missing from the API or from disk still yields a well-formed result.
        """
        jobs_by_name = {job.name: job for job in jobs}
        # Reverse each downloaded artifact's name to identify which target/env/platform it belongs to.
        dirs_by_fields: dict[tuple[str, str, str], Path] = {}
        for artifact_name, path in artifact_dirs.items():
            try:
                dirs_by_fields[split_artifact_name(artifact_name)] = path
            except ValueError:
                continue

        results: list[BatchJobResult] = []
        for batch_job in job_list:
            base = batch_job.artifact_name()
            artifact_dir = dirs_by_fields.get(split_artifact_name(base))
            results.append(
                BatchJobResult(
                    job=batch_job,
                    workflow_job=jobs_by_name.get(batch_job.name),
                    artifacts_path=str(artifact_dir) if artifact_dir is not None else None,
                    unit_artifact_name=f"unit-{base}",
                    e2e_artifact_name=f"e2e-{base}",
                    coverage_artifact_name=f"coverage-{base}",
                )
            )
        return results

    def _build_inputs(self, message: TestBatch) -> dict[str, str]:
        return {
            "batch_id": message.id,
            "checkout_sha": self._options.checkout_sha,
            "integrations": json.dumps(message.integrations),
            "job_list": json.dumps([self._job_input(job) for job in message.job_list]),
        }

    @staticmethod
    def _job_input(job: BatchJob) -> dict[str, Any]:
        """Serialize a job for the workflow, carrying the artifact name so all its files upload under
        a single folder/zip named after it (splittable later via ``split_artifact_name``)."""
        return {**dataclasses.asdict(job), "artifact_name": job.artifact_name()}

    async def _download_artifacts(self, run_id: int, log_extra: dict[str, Any]) -> tuple[Path, dict[str, Path]]:
        """Download the run's artifacts and return the run directory plus an artifact-name -> path map.

        The map keys on the GitHub artifact name (the contract a ``BatchJob`` reproduces via
        ``artifact_name``), letting the producer resolve each job's directory deterministically.
        """
        run_path = self._options.artifacts_base_path / str(run_id)
        artifact_dirs: dict[str, Path] = {}
        failures: list[tuple[int, str]] = []
        try:
            async for page in self._client.list_workflow_run_artifacts(self._options.owner, self._options.repo, run_id):
                for artifact in page.data.artifacts:
                    if artifact.expired:
                        self._logger.info(
                            "Skipping expired artifact %s (%s)",
                            artifact.id,
                            artifact.name,
                            extra=log_extra,
                        )
                        continue
                    if not artifact.archive_download_url:
                        self._logger.info(
                            "Skipping artifact %s (%s) without download URL",
                            artifact.id,
                            artifact.name,
                            extra=log_extra,
                        )
                        continue
                    target = run_path / f"{artifact.id}-{artifact.name}"
                    try:
                        await self._client.download_artifact(artifact.archive_download_url, target)
                        artifact_dirs[artifact.name] = target
                        self._logger.info("Downloaded artifact %s -> %s", artifact.id, target, extra=log_extra)
                    except Exception as exc:
                        self._logger.warning(
                            "Failed to download artifact %s (%s): %s",
                            artifact.id,
                            artifact.name,
                            exc,
                            extra=log_extra,
                        )
                        failures.append((artifact.id, artifact.name))
        except Exception:
            self._logger.warning("Failed to list workflow run artifacts", extra=log_extra, exc_info=True)
        if failures:
            self._logger.warning(
                "Artifact download had %s failures: %s",
                len(failures),
                failures,
                extra=log_extra,
            )
        return run_path, artifact_dirs
