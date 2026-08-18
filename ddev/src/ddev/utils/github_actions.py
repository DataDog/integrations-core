# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Utilities for code running inside GitHub Actions workflows."""

from __future__ import annotations

import contextlib
import json
import os

from pydantic import BaseModel, ConfigDict


class Repo(BaseModel):
    model_config = ConfigDict(extra='ignore')

    full_name: str | None = None


class PullRequestRef(BaseModel):
    model_config = ConfigDict(extra='ignore')

    repo: Repo | None = None


class EventPullRequest(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True)

    number: int | None = None
    head: PullRequestRef | None = None
    base: PullRequestRef | None = None


class PullRequestEvent(BaseModel):
    """Subset of a GitHub Actions ``pull_request`` event payload."""

    model_config = ConfigDict(extra='ignore')

    pull_request: EventPullRequest | None = None

    @classmethod
    def load(cls, path: str) -> PullRequestEvent:
        """Read and parse the event JSON file.

        Raises `OSError` if the file cannot be read, `json.JSONDecodeError`
        if the contents are not valid JSON, and `ValueError` if the parsed
        document is not a JSON object.
        """
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f'GitHub event payload at {path} is not a JSON object.')
        return cls.model_validate(data)

    @property
    def is_pull_request(self) -> bool:
        return self.pull_request is not None

    @property
    def pr_number(self) -> int | None:
        return self.pull_request.number if self.pull_request else None

    @property
    def head_repo(self) -> str | None:
        if self.pull_request and self.pull_request.head and self.pull_request.head.repo:
            return self.pull_request.head.repo.full_name
        return None

    @property
    def base_repo(self) -> str | None:
        if self.pull_request and self.pull_request.base and self.pull_request.base.repo:
            return self.pull_request.base.repo.full_name
        return None


def get_workflow_run_url() -> str | None:
    """The URL of the run this code is executing in, or None outside GitHub Actions."""
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


def write_step_summary(content: str) -> None:
    """Append *content* to the run's job summary, the Markdown panel shown on the run page.

    A silent no-op outside GitHub Actions, and an unwritable summary file is suppressed: reporting is
    never the reason a command fails.
    """
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with contextlib.suppress(OSError):
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")
