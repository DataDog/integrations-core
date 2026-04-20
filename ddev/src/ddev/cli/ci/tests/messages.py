# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from dataclasses import dataclass, field

from ddev.event_bus.orchestrator import BaseMessage


@dataclass
class BatchJob:
    """A single job entry in a TestBatch."""

    name: str = ""
    target: str = ""
    runner: str = ""
    environment: str = ""
    platform: str = ""
    unit_tests: bool = False
    e2e_tests: bool = False


@dataclass
class FailedCheck:
    """A single failed test check within a workflow."""

    name: str = ""
    url: str = ""


@dataclass
class WorkflowStatus:
    """Status of a single GitHub Actions workflow run."""

    url: str = ""
    id: int = 0
    success_count: int | None = None
    failed_count: int | None = None
    failed_checks: list[FailedCheck] = field(default_factory=list)


@dataclass
class TestBatch(BaseMessage):
    """Dispatched to trigger a matrix of test jobs."""

    job_list: list[BatchJob] = field(default_factory=list)
    jobs_count: int = 0
    integrations: list[str] = field(default_factory=list)


@dataclass
class BatchFinished(BaseMessage):
    """Emitted when a GitHub Actions test workflow has completed."""

    status: str = ""
    run_id: int = 0
    workflow_url: str = ""
    artifacts_path: str = ""


@dataclass
class UpdatePRComment(BaseMessage):
    """Emitted to request a PR comment update."""

    done: bool = False
    workflows: list[WorkflowStatus] = field(default_factory=list)
