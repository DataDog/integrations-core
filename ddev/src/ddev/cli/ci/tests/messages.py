# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ddev.event_bus.orchestrator import BaseMessage


@dataclass
class BatchJob:
    """A single job entry in a TestBatch."""

    name: str
    target: str
    runner: str
    environment: str
    platform: Literal["linux", "windows", "macos"]
    unit_tests: bool
    e2e_tests: bool


@dataclass
class FailedCheck:
    """A single failed test check within a workflow."""

    name: str
    url: str


@dataclass
class WorkflowStatus:
    """Status of a single GitHub Actions workflow run."""

    url: str
    id: int
    success_count: int | None
    failed_count: int | None
    failed_checks: list[FailedCheck]


@dataclass
class TestBatch(BaseMessage):
    """Dispatched to trigger a matrix of test jobs."""

    job_list: list[BatchJob]
    jobs_count: int
    integrations: list[str]


@dataclass
class BatchFinished(BaseMessage):
    """Emitted when a GitHub Actions test workflow has completed."""

    status: Literal["success", "failure", "skipped"]
    run_id: int
    workflow_url: str
    artifacts_path: str


@dataclass
class UpdatePRComment(BaseMessage):
    """Emitted to request a PR comment update."""

    done: bool
    workflows: list[WorkflowStatus]
