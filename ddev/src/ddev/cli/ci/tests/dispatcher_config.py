# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Per-repository Dispatcher configuration read from `.ddev/config.toml`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from ddev.cli.ci.tests.github_retries import GitHubRetryConfig
from ddev.cli.ci.tests.rate_limiting import RateLimiterFactoryConfig

if TYPE_CHECKING:
    from ddev.repo.config import RepositoryConfig


class BatchingConfig(BaseModel):
    """Policy for turning discovered test units into batched plans, read from `[dispatcher.batching]`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # 240 is GitHub's 256-job matrix cap minus a 16-job setup buffer.
    max_jobs_per_batch: int = Field(default=240, gt=0, le=240)
    # Lets an integration with more jobs than one batch holds span several batches.
    allow_integration_splitting: bool = False


class DispatcherConfig(BaseModel):
    """Per-repository Dispatcher configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    global_timeout_seconds: float = Field(default=10800.0, gt=0)  # 3 hours
    # Used when Hatch does not declare a Python version.
    default_python_version: str = Field(default="3.13", pattern=r"^\d+\.\d+$")
    batching: BatchingConfig = BatchingConfig()
    github_rate_limits: RateLimiterFactoryConfig = RateLimiterFactoryConfig()
    github_retries: GitHubRetryConfig = GitHubRetryConfig()

    @classmethod
    def from_repo_config(cls, repo_config: RepositoryConfig) -> DispatcherConfig:
        """Build a DispatcherConfig from the `/dispatcher` table of `.ddev/config.toml`."""
        return cls(**repo_config.get("/dispatcher", {}))
