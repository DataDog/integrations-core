# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for DispatcherConfig.from_repo_config."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
from ddev.cli.ci.tests.rate_limiting import RateLimiterFactoryConfig
from ddev.repo.config import RepositoryConfig
from ddev.utils.fs import Path

RepoConfigBuilder = Callable[[str], RepositoryConfig]


@pytest.fixture
def repo_config(tmp_path: Path) -> RepoConfigBuilder:
    def build(toml_content: str) -> RepositoryConfig:
        config_path = Path(tmp_path) / "config.toml"
        config_path.write_text(toml_content)
        return RepositoryConfig(config_path)

    return build


def test_from_repo_config_reads_full_dispatcher_table(repo_config: RepoConfigBuilder):
    config = repo_config(
        """
        [dispatcher]
        max_jobs_per_batch = 120
        global_timeout_seconds = 3600.0

        [dispatcher.github_rate_limits]
        total_hourly_max_rate = 1500
        slow_integrations = ["mongo", "mysql"]

        [dispatcher.github_rate_limits.default]
        max_rate = 360

        [dispatcher.github_rate_limits.slow]
        max_rate = 120
        """
    )

    result = DispatcherConfig.from_repo_config(config)

    assert result.max_jobs_per_batch == 120
    assert result.global_timeout_seconds == 3600.0
    assert result.github_rate_limits.total_hourly_max_rate == 1500
    assert result.github_rate_limits.slow_integrations == frozenset({"mongo", "mysql"})
    assert result.github_rate_limits.default.max_rate == 360
    assert result.github_rate_limits.slow.max_rate == 120


def test_from_repo_config_reads_scalars_without_rate_limits_subtable(repo_config: RepoConfigBuilder):
    config = repo_config(
        """
        [dispatcher]
        max_jobs_per_batch = 120
        global_timeout_seconds = 3600.0
        """
    )

    result = DispatcherConfig.from_repo_config(config)

    assert result.max_jobs_per_batch == 120
    assert result.global_timeout_seconds == 3600.0
    assert result.github_rate_limits == RateLimiterFactoryConfig()


def test_from_repo_config_falls_back_to_defaults_when_dispatcher_table_missing(repo_config: RepoConfigBuilder):
    config = repo_config(
        """
        validations = []
        """
    )

    result = DispatcherConfig.from_repo_config(config)

    assert result == DispatcherConfig()
