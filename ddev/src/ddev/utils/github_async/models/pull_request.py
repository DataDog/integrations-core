# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pull request models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .label import Label
from .user import GitHubUser


class PullRequestRef(BaseModel):
    """A head or base branch reference on a pull request.

    Field reference (within the `pull-request` object):
    https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
    """

    model_config = ConfigDict(extra="ignore")

    ref: str
    sha: str
    label: str | None = None  # e.g. 'octocat:new-topic'


class PullRequest(BaseModel):
    """A GitHub pull request.

    Field reference:
    https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
    """

    model_config = ConfigDict(extra="ignore")

    # Identifiers
    id: int | None = None
    number: int
    node_id: str | None = None

    # URLs
    url: str | None = None
    html_url: str
    diff_url: str | None = None
    patch_url: str | None = None

    # State
    state: str | None = None  # 'open' or 'closed'
    draft: bool = False
    merged: bool | None = None
    locked: bool = False
    merge_commit_sha: str | None = None

    # Content
    title: str | None = None
    body: str | None = None

    # People
    user: GitHubUser | None = None
    assignees: list[GitHubUser] = Field(default_factory=list)
    requested_reviewers: list[GitHubUser] = Field(default_factory=list)

    # Labels
    labels: list[Label] = Field(default_factory=list)

    # Timestamps (ISO 8601 strings; not parsed into datetime to keep the model lightweight)
    created_at: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None
    merged_at: str | None = None

    # Branch references
    head: PullRequestRef | None = None
    base: PullRequestRef | None = None
