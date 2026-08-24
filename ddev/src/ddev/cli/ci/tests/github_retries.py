# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dispatcher-facing configuration for the GitHub client's retry strategy.

Only *how hard* to try is configurable. *What* may be retried stays in
``ddev.utils.github_async.retry``, because it follows from whether an endpoint can be replayed
safely: a config file that could widen it would turn a duplicate workflow run into a setting.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ddev.utils.github_async.retry import MUTATION_RETRY, SAFE_RETRY, RetryPolicies, RetryPolicy


class RetryLimitsConfig(BaseModel):
    """Attempt and backoff limits for one class of request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempts: int = Field(default=3, ge=1)
    # Bounds the whole ladder including backoff. None leaves attempts as the only stop condition.
    timeout_seconds: float | None = Field(default=60.0, gt=0)
    wait_initial_seconds: float = Field(default=0.5, gt=0)
    wait_max_seconds: float = Field(default=10.0, gt=0)
    wait_jitter_seconds: float = Field(default=1.0, ge=0)

    def apply_to(self, policy: RetryPolicy) -> RetryPolicy:
        """*policy* with these limits, keeping the conditions it retries on."""
        return policy.replace(
            attempts=self.attempts,
            timeout=self.timeout_seconds,
            wait_initial=self.wait_initial_seconds,
            wait_max=self.wait_max_seconds,
            wait_jitter=self.wait_jitter_seconds,
        )


class GitHubRetryConfig(BaseModel):
    """Retry limits for the Dispatcher's GitHub client, read from ``[dispatcher.github_retries]``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    safe: RetryLimitsConfig = RetryLimitsConfig()
    # Fewer attempts by default: a mutation only retries when the request provably never left, which
    # a second attempt either fixes at once or is unlikely to fix at all.
    mutating: RetryLimitsConfig = RetryLimitsConfig(attempts=2)

    def to_policies(self) -> RetryPolicies:
        """Build the client's policies, these limits over the built-in conditions."""
        return RetryPolicies(
            safe=self.safe.apply_to(SAFE_RETRY),
            mutating=self.mutating.apply_to(MUTATION_RETRY),
        )
