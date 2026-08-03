# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Issue and pull-request review comment models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .user import GitHubUser


class IssueComment(BaseModel):
    """A GitHub issue (or PR) comment."""

    model_config = ConfigDict(extra="ignore")

    id: int
    body: str
    user: GitHubUser | None = None
    created_at: str | None = None
    updated_at: str | None = None
    html_url: str | None = None


class PullRequestReviewComment(BaseModel):
    """An inline review comment on a pull request diff."""

    model_config = ConfigDict(extra="ignore")

    id: int
    body: str
    path: str
    commit_id: str
    html_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    user: GitHubUser | None = None
