# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Parallel `workflow_dispatch` orchestration for `ddev release test-agent`."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.cli.release.test_agent.validation import WORKFLOW_LINUX, WORKFLOW_WINDOWS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ddev.utils.github_async import GitHubResponse
    from ddev.utils.github_async.models import WorkflowDispatchResult

    DispatchOutcome = GitHubResponse[WorkflowDispatchResult] | BaseException

# Hard-coded: the two test workflows only live on DataDog/integrations-core. Forks and other
# integrations repos (extras, marketplace) have nothing to dispatch even if the branch/tag exists,
# so deferring either component to repo metadata would just hide misconfiguration. If we ever
# ship the workflows elsewhere, plumb the target through here.
REPO_OWNER = 'DataDog'
REPO_NAME = 'integrations-core'


@dataclass(frozen=True)
class DispatchedWorkflow:
    """A workflow run created by `ddev release test-agent`."""

    label: str
    workflow_id: str
    run_id: int
    html_url: str


def dispatch_both(token: str, *, ref: str, inputs: dict[str, str]) -> tuple[DispatchedWorkflow, DispatchedWorkflow]:
    """Dispatch both workflows in parallel via the async GitHub client."""
    from ddev.utils.github_async import async_github_client

    async def run_dispatches() -> Sequence[DispatchOutcome]:
        async with async_github_client(token=token) as client:
            return await asyncio.gather(
                client.create_workflow_dispatch(
                    owner=REPO_OWNER,
                    repo=REPO_NAME,
                    workflow_id=WORKFLOW_LINUX,
                    ref=ref,
                    inputs=inputs,
                    return_run_details=True,
                ),
                client.create_workflow_dispatch(
                    owner=REPO_OWNER,
                    repo=REPO_NAME,
                    workflow_id=WORKFLOW_WINDOWS,
                    ref=ref,
                    inputs=inputs,
                    return_run_details=True,
                ),
                return_exceptions=True,
            )

    return extract_dispatched_workflows(asyncio.run(run_dispatches()))


def extract_dispatched_workflows(results: Sequence[DispatchOutcome]) -> tuple[DispatchedWorkflow, DispatchedWorkflow]:
    """Pull workflow runs out of two gather results, raising on any exception with a partial-success hint.

    `asyncio.gather(return_exceptions=True)` captures `CancelledError`/`KeyboardInterrupt`
    (`BaseException` subclasses, not `Exception`) into its result list. Re-raise those first
    so flow-control exceptions propagate cleanly instead of being wrapped in `RuntimeError`.
    """
    linux_result, windows_result = results

    for result in (linux_result, windows_result):
        if isinstance(result, BaseException) and not isinstance(result, Exception):
            raise result

    if isinstance(linux_result, BaseException):
        if isinstance(windows_result, BaseException):
            raise RuntimeError(
                f'Both dispatches failed. Linux: {linux_result!r}. Windows: {windows_result!r}.'
            ) from linux_result
        sibling = windows_result.data.html_url
        raise RuntimeError(
            f'Linux dispatch failed: {linux_result}. The other workflow was dispatched at {sibling}.'
        ) from linux_result

    if isinstance(windows_result, BaseException):
        sibling = linux_result.data.html_url
        raise RuntimeError(
            f'Windows dispatch failed: {windows_result}. The other workflow was dispatched at {sibling}.'
        ) from windows_result

    return (
        DispatchedWorkflow(
            label='Linux',
            workflow_id=WORKFLOW_LINUX,
            run_id=linux_result.data.workflow_run_id,
            html_url=linux_result.data.html_url,
        ),
        DispatchedWorkflow(
            label='Windows',
            workflow_id=WORKFLOW_WINDOWS,
            run_id=windows_result.data.workflow_run_id,
            html_url=windows_result.data.html_url,
        ),
    )
