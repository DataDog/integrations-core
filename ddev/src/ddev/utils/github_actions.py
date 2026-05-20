# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Utilities for code running inside GitHub Actions workflows."""

from __future__ import annotations

import json

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


class GitHubEvent(BaseModel):
    """Subset of a GitHub Actions ``pull_request`` event payload."""

    model_config = ConfigDict(extra='ignore')

    pull_request: EventPullRequest | None = None

    @classmethod
    def load(cls, path: str) -> GitHubEvent:
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
