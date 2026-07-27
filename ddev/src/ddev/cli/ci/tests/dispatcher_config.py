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


class BatchingConfig(BaseModel):
    """Policy for turning discovered test units into batched ``TestBatch`` plans.

    Read from the ``[dispatcher.batching]`` table. ``max_jobs_per_batch`` caps every batch (256
    GitHub job cap minus a 16-job setup buffer, the safe max). ``allow_integration_splitting``
    permits a single integration whose job count exceeds ``max_jobs_per_batch`` to span multiple
    capacity-bounded batches.

    Splitting a job's unit and E2E facets into separate jobs is not implemented yet; the plan
    currently emits one job per resolved environment that produces both facets.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_jobs_per_batch: int = Field(default=240, gt=0, le=240)
    allow_integration_splitting: bool = False


class DispatcherConfig(BaseModel):
    """Per-repository Dispatcher configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    global_timeout_seconds: float = Field(default=10800.0, gt=0)  # 3 hours
    # Used only where a Hatch environment declares no Python of its own, and for targets that
    # define no environments at all.
    default_python_version: str = Field(default="3.13", pattern=r"^\d+\.\d+$")
    batching: BatchingConfig = BatchingConfig()
    github_rate_limits: RateLimiterFactoryConfig = RateLimiterFactoryConfig()

    @classmethod
    def from_repo_config(cls, repo_config: RepositoryConfig) -> DispatcherConfig:
        """Build a DispatcherConfig from the `/dispatcher` table of `.ddev/config.toml`."""
        return cls(**repo_config.get("/dispatcher", {}))
