# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Per-repository Dispatcher configuration read from `.ddev/config.toml`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from ddev.cli.ci.tests.rate_limiting import RateLimiterFactoryConfig
from ddev.utils.github_async.retry import MUTATION_RETRY, SAFE_RETRY, RetryPolicies, RetryPolicy

if TYPE_CHECKING:
    from ddev.repo.config import RepositoryConfig


class BatchingConfig(BaseModel):
    """Policy for turning discovered test units into batched plans, read from `[dispatcher.batching]`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # 240 is GitHub's 256-job matrix cap minus a 16-job setup buffer.
    max_jobs_per_batch: int = Field(default=240, gt=0, le=240)
    # Lets an integration with more jobs than one batch holds span several batches.
    allow_integration_splitting: bool = False


class RetryLimitsConfig(BaseModel):
    """Attempt and backoff limits for one class of GitHub request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempts: int = Field(default=3, ge=1)
    # Bounds the whole ladder including backoff. None leaves attempts as the only stop condition.
    timeout_seconds: float | None = Field(default=60.0, gt=0)
    wait_initial_seconds: float = Field(default=0.5, gt=0)
    wait_max_seconds: float = Field(default=10.0, gt=0)
    wait_jitter_seconds: float = Field(default=1.0, ge=0)

    def apply_to(self, policy: RetryPolicy) -> RetryPolicy:
        """`policy` with these limits, keeping the conditions it retries on."""
        return policy.replace(
            attempts=self.attempts,
            timeout=self.timeout_seconds,
            wait_initial=self.wait_initial_seconds,
            wait_max=self.wait_max_seconds,
            wait_jitter=self.wait_jitter_seconds,
        )


class GitHubRetryConfig(BaseModel):
    """Retry limits for the GitHub client, read from `[dispatcher.github_retries]`.

    Only how hard to try is configurable. What may be retried follows from whether an endpoint can be
    replayed, so widening it from a config file would make a duplicate side effect a setting.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    safe: RetryLimitsConfig = RetryLimitsConfig()
    mutating: RetryLimitsConfig = RetryLimitsConfig(attempts=2)

    def to_policies(self) -> RetryPolicies:
        """Build the client's policies: these limits over the built-in conditions."""
        return RetryPolicies(
            safe=self.safe.apply_to(SAFE_RETRY),
            mutating=self.mutating.apply_to(MUTATION_RETRY),
        )


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
