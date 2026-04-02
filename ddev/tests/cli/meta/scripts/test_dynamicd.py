# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for DynamicD context_builder functions.

These tests verify that dashboard parsing correctly extracts metrics, tags,
and tag values from real integration dashboards.
"""

import pytest

from ddev.repo.core import Repository


@pytest.fixture
def real_repo(local_repo):
    """Get a real repository instance pointing to integrations-core."""
    return Repository(local_repo.name, str(local_repo))


# Test integrations with their expected metric prefixes
# Format: (integration_name, metric_prefix, prefix_is_exact)
INTEGRATION_TEST_CASES = [
    ('redisdb', 'redis.', True),
    ('postgres', 'postgresql.', False),  # Don't check exact prefix match
    ('cassandra', 'cassandra.', True),
    ('celery', 'celery.flower.', False),  # Celery uses celery.flower. prefix
]


class TestReadDashboardMetrics:
    """Tests for _read_dashboard_metrics function."""

    @pytest.mark.parametrize('integration_name,metric_prefix,check_exact', INTEGRATION_TEST_CASES)
    def test_extracts_metrics_from_dashboard(self, real_repo, integration_name, metric_prefix, check_exact):
        """Dashboard should have metrics extracted for the integration."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_dashboard_metrics

        integration = real_repo.integrations.get(integration_name)
        metrics = _read_dashboard_metrics(integration, metric_prefix)

        assert len(metrics) > 0, f"Should extract at least some metrics from {integration_name} dashboard"
        if check_exact:
            assert all(m.startswith(metric_prefix) for m in metrics), f"All metrics should have {metric_prefix} prefix"

    def test_returns_empty_for_integration_without_dashboard(self, tmp_path):
        """Integration without dashboards should return empty list."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_dashboard_metrics

        fake_integration = type('FakeIntegration', (), {'path': tmp_path})()

        metrics = _read_dashboard_metrics(fake_integration, 'fake.')
        assert metrics == [], "Should return empty list when no dashboards exist"


class TestReadDashboardTags:
    """Tests for _read_dashboard_tags function."""

    @pytest.mark.parametrize('integration_name,metric_prefix,check_exact', INTEGRATION_TEST_CASES)
    def test_extracts_tags_from_dashboard(self, real_repo, integration_name, metric_prefix, check_exact):
        """Dashboard should have tags extracted for grouping."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_dashboard_tags

        integration = real_repo.integrations.get(integration_name)
        tags = _read_dashboard_tags(integration)

        assert isinstance(tags, dict), "Should return a dict"

    def test_returns_empty_for_integration_without_dashboard(self, tmp_path):
        """Integration without dashboards should return empty dict."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_dashboard_tags

        fake_integration = type('FakeIntegration', (), {'path': tmp_path})()

        tags = _read_dashboard_tags(fake_integration)
        assert tags == {}, "Should return empty dict when no dashboards exist"


class TestReadDashboardTagValues:
    """Tests for _read_dashboard_tag_values function."""

    @pytest.mark.parametrize('integration_name,metric_prefix,check_exact', INTEGRATION_TEST_CASES)
    def test_extracts_tag_values_from_dashboard(self, real_repo, integration_name, metric_prefix, check_exact):
        """Should extract specific tag:value pairs from dashboard queries."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_dashboard_tag_values

        integration = real_repo.integrations.get(integration_name)
        tag_values = _read_dashboard_tag_values(integration)

        assert isinstance(tag_values, dict), "Should return a dict"

    def test_returns_empty_for_integration_without_dashboard(self, tmp_path):
        """Integration without dashboards should return empty dict."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_dashboard_tag_values

        fake_integration = type('FakeIntegration', (), {'path': tmp_path})()

        tag_values = _read_dashboard_tag_values(fake_integration)
        assert tag_values == {}, "Should return empty dict when no dashboards exist"


class TestBuildContext:
    """Tests for build_context function."""

    @pytest.mark.parametrize('integration_name,metric_prefix,check_exact', INTEGRATION_TEST_CASES)
    def test_builds_context_for_integration(self, real_repo, integration_name, metric_prefix, check_exact):
        """Should build complete context for integration."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import build_context

        integration = real_repo.integrations.get(integration_name)
        context = build_context(integration)

        assert context.name == integration_name
        assert len(context.metrics) > 0, f"{integration_name} should have metrics"
        if check_exact:
            assert context.metric_prefix == metric_prefix

    def test_all_metrics_mode(self, real_repo):
        """all_metrics mode should set the flag in context."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import build_context

        redis = real_repo.integrations.get('redisdb')

        context_normal = build_context(redis, all_metrics=False)
        context_all = build_context(redis, all_metrics=True)

        assert context_normal.all_metrics_mode is False
        assert context_all.all_metrics_mode is True

    def test_to_prompt_context_generates_string(self, real_repo):
        """to_prompt_context should generate a non-empty string."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import build_context

        redis = real_repo.integrations.get('redisdb')
        context = build_context(redis)

        prompt = context.to_prompt_context()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert 'redis' in prompt.lower()


class TestReadMetrics:
    """Tests for _read_metrics function."""

    @pytest.mark.parametrize('integration_name,metric_prefix,check_exact', INTEGRATION_TEST_CASES)
    def test_reads_metrics_from_metadata_csv(self, real_repo, integration_name, metric_prefix, check_exact):
        """Should read metrics from metadata.csv."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_metrics

        integration = real_repo.integrations.get(integration_name)
        metrics = _read_metrics(integration)

        assert len(metrics) > 0, f"{integration_name} should have metrics in metadata.csv"
        assert all('metric_name' in m for m in metrics), "Each metric should have a metric_name"


class TestReadServiceChecks:
    """Tests for _read_service_checks function."""

    def test_reads_service_checks(self, real_repo):
        """Should read service checks from service_checks.json."""
        from ddev.cli.meta.scripts._dynamicd.context_builder import _read_service_checks

        redis = real_repo.integrations.get('redisdb')
        checks = _read_service_checks(redis)

        assert len(checks) > 0, "Redis should have service checks"
        assert all('name' in c for c in checks), "Each check should have a name"
