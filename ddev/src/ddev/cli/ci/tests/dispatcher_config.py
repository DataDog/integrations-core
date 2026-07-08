# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Per-repository Dispatcher configuration read from `.ddev/config.toml`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from ddev.cli.ci.tests.rate_limiting import RateLimiterFactoryConfig

if TYPE_CHECKING:
    from ddev.repo.config import RepositoryConfig


class DispatcherConfig(BaseModel):
    """Per-repository Dispatcher configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_jobs_per_batch: int = Field(default=240, gt=0, le=240)  # 256 GitHub job cap - 16-job setup buffer; the safe max
    global_timeout_seconds: float = Field(default=10800.0, gt=0)  # 3 hours
    github_rate_limits: RateLimiterFactoryConfig = RateLimiterFactoryConfig()

    @classmethod
    def from_repo_config(cls, repo_config: RepositoryConfig) -> DispatcherConfig:
        """Build a DispatcherConfig from the `/dispatcher` table of `.ddev/config.toml`."""
        return cls(**repo_config.get("/dispatcher", {}))
