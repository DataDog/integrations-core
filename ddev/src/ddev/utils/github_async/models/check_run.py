# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub Checks API models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CheckRun(BaseModel):
    """A GitHub Checks API check run."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    status: str
    conclusion: str | None = None
    html_url: str | None = None
    head_sha: str | None = None
