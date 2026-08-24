# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for turning the Dispatcher's retry configuration into client policies."""

from __future__ import annotations

import httpx

from ddev.cli.ci.tests.github_retries import GitHubRetryConfig, RetryLimitsConfig


def test_configured_limits_reach_the_policies():
    """The config exists to tune the ladder, so its numbers have to arrive on the policy."""
    config = GitHubRetryConfig(
        safe=RetryLimitsConfig(attempts=7, timeout_seconds=120.0, wait_max_seconds=30.0),
        mutating=RetryLimitsConfig(attempts=1),
    )

    policies = config.to_policies()

    assert policies.safe.attempts == 7
    assert policies.safe.timeout == 120.0
    assert policies.safe.wait_max == 30.0
    assert policies.mutating.attempts == 1


def test_configuring_the_limits_does_not_change_what_is_retried():
    """Widening the conditions from a config file would make a duplicate workflow run a setting.

    Only the ladder is configurable, so each tier has to keep the conditions it was built with: the
    safe tier still replays a 502, and the mutating tier still refuses one.
    """
    policies = GitHubRetryConfig(safe=RetryLimitsConfig(attempts=9)).to_policies()
    request = httpx.Request("GET", "https://api.github.com/x")
    server_error = httpx.HTTPStatusError("boom", request=request, response=httpx.Response(502, request=request))

    assert policies.safe.should_retry(server_error)
    assert not policies.mutating.should_retry(server_error)
    assert policies.mutating.should_retry(httpx.ConnectError("refused"))
