# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub user model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GitHubUser(BaseModel):
    """A GitHub user as returned by the REST API.

    Field reference:
    https://docs.github.com/en/rest/users/users#get-a-user
    """

    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    login: str | None = None
    html_url: str | None = None
    type: str | None = None  # 'User', 'Bot', 'Organization', etc.
