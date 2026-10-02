"""Shared helpers and data contracts for the master CI triage scripts.

``detect.py`` produces ``RunRecord``s; ``notify.py`` and ``enrich.py`` consume
them from ``triage_output.json``. Keeping ``env()`` and the record shape in one
place stops the three sibling scripts from drifting.
"""

from __future__ import annotations

import os
from datetime import datetime
from enum import StrEnum
from typing import TypedDict


class Severity(StrEnum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    NONE = "NONE"


class FailedTarget(TypedDict):
    target: str
    job_name: str
    job_id: str
    gh_job_id: str
    url: str
    leg_count: int


class RunRecord(TypedDict):
    run_id: int
    sha: str
    short_sha: str
    title: str
    actor: str
    workflow: str
    url: str
    created_at: str
    failed_targets: list[FailedTarget]
    failed_count: int
    other_failures: int
    severity: Severity


class TriageOutput(TypedDict):
    mode: str
    severity: Severity
    runs: list[RunRecord]
    non_test_failure_count: int
    enrichment_jobs: list[dict[str, str]]
    dashboard_url: str


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def parse_github_timestamp(ts: str) -> datetime:
    """Parse a GitHub ISO-8601 timestamp, normalizing the trailing ``Z``."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))
