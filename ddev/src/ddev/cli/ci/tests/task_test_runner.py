# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from pathlib import Path
from typing import Literal

from ddev.cli.ci.tests.messages import BatchFinished, TestBatch
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_async import AsyncGitHubClient


def _conclusion_to_status(conclusion: str | None) -> Literal["success", "failure", "skipped"]:
    """Map a GitHub Actions conclusion string to a BatchFinished status."""
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
        self._logger = logging.getLogger(f"{__name__}.{name}")

    async def process_message(self, message: TestBatch) -> None:
        inputs = self._build_inputs(message)

        dispatch = await self._client.create_workflow_dispatch(
            self._owner, self._repo, self._workflow_id, ref=self._ref, inputs=inputs
        )
        run_id = dispatch.data.workflow_run_id
        self._logger.info("Dispatched batch %s as run %s", message.id, run_id)

        run = await self._client.get_workflow_run(self._owner, self._repo, run_id)
        workflow_url = run.data.html_url or ""

        check = await self._client.create_check_run(
            self._owner,
            self._repo,
            name=f"test-batch/{message.id}",
            head_sha=self._base_sha,
            status="in_progress",
            details_url=workflow_url or None,
        )
        check_run_id = check.data.id

        while run.data.status != "completed":
            await asyncio.sleep(self._poll_interval_seconds)
            run = await self._client.get_workflow_run(self._owner, self._repo, run_id)

        artifacts_path = await self._download_artifacts(run_id)

        self.submit_message(
            BatchFinished(
                id=message.id,
                status=_conclusion_to_status(run.data.conclusion),
                run_id=run_id,
                workflow_url=workflow_url,
                artifacts_path=str(artifacts_path),
            )
        )

        await self._client.update_check_run(
            self._owner,
            self._repo,
            check_run_id,
            status="completed",
            conclusion=run.data.conclusion or "neutral",
            details_url=workflow_url or None,
        )

    def _build_inputs(self, message: TestBatch) -> dict[str, str]:
        return {
            "batch_id": message.id,
            "checkout_sha": self._checkout_sha,
            "integrations": json.dumps(message.integrations),
            "job_list": json.dumps([dataclasses.asdict(job) for job in message.job_list]),
        }

    async def _download_artifacts(self, run_id: int) -> Path:
        run_path = self._artifacts_base_path / str(run_id)
        async for page in self._client.list_workflow_run_artifacts(self._owner, self._repo, run_id):
            for artifact in page.data.artifacts:
                if artifact.expired or not artifact.archive_download_url:
                    continue
                await self._client.download_artifact(
                    artifact.archive_download_url,
                    run_path / artifact.name,
                )
        return run_path
