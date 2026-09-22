# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Git data and repository-contents models."""

from __future__ import annotations

from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict


class GitObject(BaseModel):
    """The object a git reference points at.

    Field reference (within the `git-ref` object, whose `object` is required with
    `type`, `sha`, `url`):
    https://docs.github.com/en/rest/git/refs#get-a-reference
    """

    model_config = ConfigDict(extra="ignore")

    type: str
    sha: str
    url: str


class GitReference(BaseModel):
    """A git reference (branch or tag).

    Field reference (`git-ref` requires `ref`, `node_id`, `url`, `object`):
    https://docs.github.com/en/rest/git/refs#get-a-reference
    """

    model_config = ConfigDict(extra="ignore")

    ref: str
    node_id: str
    url: str
    object: GitObject


class ContentType(StrEnum):
    """The type of a repository content entry returned for a file path.

    The `content-file` schema declares `type` as `enum: [file]`.
    Reference:
    https://docs.github.com/en/rest/repos/contents#get-repository-content
    """

    FILE = auto()


class FileContent(BaseModel):
    """A single file's content and metadata.

    Field reference (`content-file`):
    https://docs.github.com/en/rest/repos/contents#get-repository-content
    """

    model_config = ConfigDict(extra="ignore")

    type: ContentType
    encoding: str
    size: int
    name: str
    path: str
    content: str
    sha: str


class CommitInfo(BaseModel):
    """The commit produced by a create-or-update-contents call.

    Field reference (the `commit` object within `file-commit`):
    https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents
    """

    model_config = ConfigDict(extra="ignore")

    sha: str | None = None
    html_url: str | None = None


class FileCommit(BaseModel):
    """The result of creating or updating file contents.

    Field reference (`file-commit` requires `content` and `commit`; `content` is nullable and
    ignored here because callers only need the commit):
    https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents
    """

    model_config = ConfigDict(extra="ignore")

    commit: CommitInfo
