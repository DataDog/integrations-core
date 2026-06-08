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

from ddev.cli.ci.tests.messages import BatchFinished, TestBatch
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import WorkflowRun


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
            timed_out = False
            if run.data.status != "completed":
                completed = await self._poll_until_complete(run_id, log_extra)
                if completed is None:
                    final_conclusion = "timed_out"
                    timed_out = True
                    self._logger.warning("Workflow polling timed out", extra=log_extra)
                else:
                    run = completed
            else:
                self._logger.info("Workflow completed", extra=log_extra)

            if timed_out:
                finished = BatchFinished(
                    id=message.id,
                    status="failure",
                    run_id=run_id,
                    workflow_url=workflow_url,
                    artifacts_path="",
                    timed_out=True,
                )
            else:
                raw = run.data.conclusion
                if raw is None:
                    self._logger.warning("Workflow completed with null conclusion", extra=log_extra)
                final_conclusion = raw or "neutral"

                artifacts_path = await self._download_artifacts(run_id, log_extra)
                self._logger.info("Artifacts downloaded", extra=log_extra)

                finished = BatchFinished(
                    id=message.id,
                    status=_conclusion_to_status(raw),
                    run_id=run_id,
                    workflow_url=workflow_url,
                    artifacts_path=str(artifacts_path),
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

    def _build_inputs(self, message: TestBatch) -> dict[str, str]:
        return {
            "batch_id": message.id,
            "checkout_sha": self._options.checkout_sha,
            "integrations": json.dumps(message.integrations),
            "job_list": json.dumps([dataclasses.asdict(job) for job in message.job_list]),
        }

    async def _download_artifacts(self, run_id: int, log_extra: dict[str, Any]) -> Path:
        run_path = self._options.artifacts_base_path / str(run_id)
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
        return run_path
