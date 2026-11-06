# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pull request models."""

from __future__ import annotations

from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict, Field

from .label import Label
from .user import GitHubUser


class PullRequestState(StrEnum):
    """The state of a pull request.

    The `pull-request` schema declares `state` as `enum: [open, closed]`.
    Reference:
    https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
    """

    OPEN = auto()
    CLOSED = auto()


class PullRequestFileStatus(StrEnum):
    """How a file was changed by a pull request.

    The `diff-entry` schema declares `status` as
    `enum: [added, removed, modified, renamed, copied, changed, unchanged]`.
    Reference:
    https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files
    """

    ADDED = auto()
    REMOVED = auto()
    MODIFIED = auto()
    RENAMED = auto()
    COPIED = auto()
    CHANGED = auto()
    UNCHANGED = auto()


class PullRequestFile(BaseModel):
    """One entry of a pull request's file list.

    Only the fields needed to reconstruct a change are modelled; the schema's diff statistics and
    blob URLs are ignored. `previous_filename` is populated for renames and copies, and is the
    source path.

    Field reference (the `diff-entry` schema):
    https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files
    """

    model_config = ConfigDict(extra="ignore")

    filename: str
    status: PullRequestFileStatus
    previous_filename: str | None = None


class PullRequestRepo(BaseModel):
    """The repository a pull request's head or base branch lives in."""

    model_config = ConfigDict(extra="ignore")

    full_name: str  # e.g. 'DataDog/integrations-core'


class PullRequestRef(BaseModel):
    """A head or base branch reference on a pull request.

    Field reference (within the `pull-request` object):
    https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
    """

    model_config = ConfigDict(extra="ignore")

    ref: str
    sha: str
    label: str | None = None  # e.g. 'octocat:new-topic'
    # Null once the head repository is deleted, which GitHub allows while the pull request survives.
    repo: PullRequestRepo | None = None


class PullRequestSimple(BaseModel):
    """A GitHub pull request as the list endpoints return it.

    GitHub has two pull request schemas. `pull-request-simple` is what the list endpoints return,
    and it is a strict subset of `pull-request`: it omits the diff totals and the merge state,
    without marking them null. Whether those fields are available is therefore a property of the
    endpoint that was called, not of the pull request, which is why the two are modelled
    separately rather than as one class with everything optional. `PullRequest` adds them.

    Field reference (the `pull-request-simple` schema):
    https://docs.github.com/en/rest/pulls/pulls#list-pull-requests
    """

    model_config = ConfigDict(extra="ignore")

    # `number` and `html_url` are required because consumers (notably `ddev release port-commit`)
    # read them directly without nullability checks. Other fields stay optional to keep parsing
    # resilient when an endpoint returns an abbreviated payload.

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
    state: PullRequestState | None = None
    draft: bool = False
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


class PullRequest(PullRequestSimple):
    """A GitHub pull request as the single-object endpoints return it.

    Adds the fields `pull-request` declares and `pull-request-simple` omits. `changed_files` is
    required: the schema declares it as a required integer, and a caller listing a pull request's
    files needs it to tell a complete list from a silently truncated one. Validation failing is
    the point, since the alternative is reading a missing count as an empty diff and testing
    nothing.

    Field reference (the `pull-request` schema):
    https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request
    """

    changed_files: int

    # Also full-only, but left optional: `port-commit` reads it as a boolean and the schema's other
    # additions (`additions`, `deletions`, `commits`, `mergeable`, ...) are not modelled at all.
    merged: bool | None = None
