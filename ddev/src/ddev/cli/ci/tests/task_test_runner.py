# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from pathlib import Path
from typing import Any, Literal

import httpx

from ddev.cli.ci.tests.messages import BatchFinished, TestBatch
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse, WorkflowRun


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


class TaskTestRunner(AsyncProcessor[TestBatch]):
    """
    Launches a ``test-batch.yaml`` workflow run for a ``TestBatch``, waits for it
    to complete, downloads its artifacts, and emits a ``BatchFinished`` message.

    No throttling and no DispatcherConfig — those land in later tiers.

    Note: ``base_sha`` is currently used as the check run's ``head_sha`` while the
    workflow input receives ``checkout_sha`` (the merge commit). The asymmetry —
    check on PR head, workflow on merge commit — is intentional for now, but the
    semantics will be revisited once ``BatchFinished`` consumers are settled. See
    PR #23518 review thread.
    """

    def __init__(
        self,
        name: str,
        client: AsyncGitHubClient,
        owner: str,
        repo: str,
        workflow_id: str | int,
        ref: str,
        base_sha: str,
        checkout_sha: str,
        artifacts_base_path: Path,
        poll_interval_seconds: float = 30.0,
        max_wait_seconds: float = 1800.0,
        transient_retry_attempts: int = 3,
        transient_retry_base_seconds: float = 1.0,
        transient_retry_factor: float = 2.0,
    ) -> None:
        super().__init__(name)
        self._client = client
        self._owner = owner
        self._repo = repo
        self._workflow_id = workflow_id
        self._ref = ref
        self._base_sha = base_sha
        self._checkout_sha = checkout_sha
        self._artifacts_base_path = artifacts_base_path
        self._poll_interval_seconds = poll_interval_seconds
        self._max_wait_seconds = max_wait_seconds
        self._transient_retry_attempts = transient_retry_attempts
        self._transient_retry_base_seconds = transient_retry_base_seconds
        self._transient_retry_factor = transient_retry_factor
        self._logger = logging.getLogger(f"{__name__}.{name}")

    async def process_message(self, message: TestBatch) -> None:
        inputs = self._build_inputs(message)
        log_extra: dict[str, Any] = {"batch_id": message.id}

        dispatch = await self._client.create_workflow_dispatch(
            self._owner, self._repo, self._workflow_id, ref=self._ref, inputs=inputs
        )
        run_id = dispatch.data.workflow_run_id
        log_extra["run_id"] = run_id
        self._logger.info("Dispatched batch", extra=log_extra)

        run = await self._get_workflow_run_with_retry(run_id, log_extra)
        workflow_url = run.data.html_url or ""
        log_extra["workflow_url"] = workflow_url

        check = await self._client.create_check_run(
            self._owner,
            self._repo,
            name=f"test-batch/{message.id}",
            head_sha=self._base_sha,
            status="in_progress",
            details_url=workflow_url or None,
        )
        check_run_id = check.data.id
        log_extra["check_run_id"] = check_run_id
        self._logger.info("Check run created", extra=log_extra)

        final_conclusion: str = "cancelled"
        finished: BatchFinished | None = None
        try:
            if run.data.status != "completed":
                completed = await self._poll_until_complete(run_id, log_extra)
                if completed is None:
                    final_conclusion = "timed_out"
                    self._logger.warning("Workflow polling timed out", extra=log_extra)
                    return
                run = completed
            else:
                self._logger.info("Workflow completed", extra=log_extra)

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
            await self._client.update_check_run(
                self._owner,
                self._repo,
                check_run_id,
                status="completed",
                conclusion=final_conclusion,
                details_url=workflow_url or None,
            )
            self._logger.info("Check run closed", extra={**log_extra, "conclusion": final_conclusion})

        if finished is not None:
            self.submit_message(finished)
            self._logger.info("BatchFinished emitted", extra=log_extra)

    async def _poll_until_complete(self, run_id: int, log_extra: dict[str, Any]) -> GitHubResponse[WorkflowRun] | None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._max_wait_seconds
        while True:
            if loop.time() >= deadline:
                return None
            await asyncio.sleep(self._poll_interval_seconds)
            run = await self._get_workflow_run_with_retry(run_id, log_extra)
            if run.data.status == "completed":
                self._logger.info("Workflow completed", extra=log_extra)
                return run

    async def _get_workflow_run_with_retry(self, run_id: int, log_extra: dict[str, Any]) -> GitHubResponse[WorkflowRun]:
        last_exc: Exception | None = None
        delay = self._transient_retry_base_seconds
        for attempt in range(1, self._transient_retry_attempts + 1):
            try:
                return await self._client.get_workflow_run(self._owner, self._repo, run_id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise
                last_exc = exc
            except httpx.TransportError as exc:
                last_exc = exc
            self._logger.warning(
                "Transient failure on get_workflow_run (attempt %s/%s): %s",
                attempt,
                self._transient_retry_attempts,
                last_exc,
                extra=log_extra,
            )
            if attempt < self._transient_retry_attempts:
                await asyncio.sleep(delay)
                delay *= self._transient_retry_factor
        assert last_exc is not None
        raise last_exc

    def _build_inputs(self, message: TestBatch) -> dict[str, str]:
        return {
            "batch_id": message.id,
            "checkout_sha": self._checkout_sha,
            "integrations": json.dumps(message.integrations),
            "job_list": json.dumps([dataclasses.asdict(job) for job in message.job_list]),
        }

    async def _download_artifacts(self, run_id: int, log_extra: dict[str, Any]) -> Path:
        run_path = self._artifacts_base_path / str(run_id)
        failures: list[tuple[int, str]] = []
        async for page in self._client.list_workflow_run_artifacts(self._owner, self._repo, run_id):
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
        if failures:
            self._logger.warning(
                "Artifact download had %s failures: %s",
                len(failures),
                failures,
                extra=log_extra,
            )
        return run_path
