"""Shared helpers and data contracts for the master CI triage scripts.

``detect.py`` produces ``RunRecord``s; ``notify.py`` and ``enrich.py`` consume
them from ``triage_output.json``. Keeping ``env()`` and the record shape in one
place stops the three sibling scripts from drifting.
"""

from __future__ import annotations

import os
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
    severity: str


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()
