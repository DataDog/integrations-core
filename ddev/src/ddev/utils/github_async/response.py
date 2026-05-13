# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Generic response wrapper for the async GitHub client."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GitHubResponse[T](BaseModel):
    """Generic wrapper for a GitHub API response."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: T = Field(...)
    headers: dict[str, str] = Field(default_factory=dict)
