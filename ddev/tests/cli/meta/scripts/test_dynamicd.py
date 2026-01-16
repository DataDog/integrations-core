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


class TestReadDashboardMetrics:
    """Tests for _read_dashboard_metrics function."""

    def test_extracts_metrics_from_redis_dashboard(self, real_repo):
        """Redis dashboard should have redis.* metrics extracted."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_metrics

        redis = real_repo.integrations.get('redisdb')
        metrics = _read_dashboard_metrics(redis, 'redis.')

        assert len(metrics) > 0, "Should extract at least some metrics from redis dashboard"
        assert all(m.startswith('redis.') for m in metrics), "All metrics should have redis. prefix"

    def test_extracts_metrics_from_postgres_dashboard(self, real_repo):
        """Postgres dashboard should have postgres.* metrics extracted."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_metrics

        postgres = real_repo.integrations.get('postgres')
        metrics = _read_dashboard_metrics(postgres, 'postgresql.')

        assert len(metrics) > 0, "Should extract at least some metrics from postgres dashboard"

    def test_extracts_metrics_from_cassandra_dashboard(self, real_repo):
        """Cassandra dashboard should have cassandra.* metrics extracted."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_metrics

        cassandra = real_repo.integrations.get('cassandra')
        metrics = _read_dashboard_metrics(cassandra, 'cassandra.')

        assert len(metrics) > 0, "Should extract at least some metrics from cassandra dashboard"
        assert all(m.startswith('cassandra.') for m in metrics), "All metrics should have cassandra. prefix"

    def test_extracts_metrics_from_celery_dashboard(self, real_repo):
        """Celery dashboard should have celery.* metrics extracted."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_metrics

        celery = real_repo.integrations.get('celery')
        # Celery uses celery.flower. prefix
        metrics = _read_dashboard_metrics(celery, 'celery.flower.')

        assert len(metrics) > 0, "Should extract at least some metrics from celery dashboard"
        assert all('celery' in m.lower() for m in metrics), "All metrics should contain celery"

    def test_returns_empty_for_integration_without_dashboard(self, tmp_path):
        """Integration without dashboards should return empty list."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_metrics

        fake_integration = type('FakeIntegration', (), {'path': tmp_path})()

        metrics = _read_dashboard_metrics(fake_integration, 'fake.')
        assert metrics == [], "Should return empty list when no dashboards exist"


class TestReadDashboardTags:
    """Tests for _read_dashboard_tags function."""

    def test_extracts_tags_from_redis_dashboard(self, real_repo):
        """Redis dashboard should have tags extracted for grouping."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_tags

        redis = real_repo.integrations.get('redisdb')
        tags = _read_dashboard_tags(redis)

        assert isinstance(tags, dict), "Should return a dict"

    def test_returns_empty_for_integration_without_dashboard(self, tmp_path):
        """Integration without dashboards should return empty dict."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_tags

        fake_integration = type('FakeIntegration', (), {'path': tmp_path})()

        tags = _read_dashboard_tags(fake_integration)
        assert tags == {}, "Should return empty dict when no dashboards exist"


class TestReadDashboardTagValues:
    """Tests for _read_dashboard_tag_values function."""

    def test_extracts_tag_values_from_dashboard(self, real_repo):
        """Should extract specific tag:value pairs from dashboard queries."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_tag_values

        redis = real_repo.integrations.get('redisdb')
        tag_values = _read_dashboard_tag_values(redis)

        assert isinstance(tag_values, dict), "Should return a dict"

    def test_returns_empty_for_integration_without_dashboard(self, tmp_path):
        """Integration without dashboards should return empty dict."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_dashboard_tag_values

        fake_integration = type('FakeIntegration', (), {'path': tmp_path})()

        tag_values = _read_dashboard_tag_values(fake_integration)
        assert tag_values == {}, "Should return empty dict when no dashboards exist"


class TestBuildContext:
    """Tests for build_context function."""

    def test_builds_context_for_redis(self, real_repo):
        """Should build complete context for redis integration."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import build_context

        redis = real_repo.integrations.get('redisdb')
        context = build_context(redis)

        assert context.name == 'redisdb'
        assert context.display_name is not None
        assert len(context.metrics) > 0, "Redis should have metrics"
        assert context.metric_prefix == 'redis.'

    def test_builds_context_for_postgres(self, real_repo):
        """Should build complete context for postgres integration."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import build_context

        postgres = real_repo.integrations.get('postgres')
        context = build_context(postgres)

        assert context.name == 'postgres'
        assert len(context.metrics) > 0, "Postgres should have metrics"

    def test_builds_context_for_cassandra(self, real_repo):
        """Should build complete context for cassandra integration."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import build_context

        cassandra = real_repo.integrations.get('cassandra')
        context = build_context(cassandra)

        assert context.name == 'cassandra'
        assert len(context.metrics) > 0, "Cassandra should have metrics"
        assert context.metric_prefix == 'cassandra.'

    def test_builds_context_for_celery(self, real_repo):
        """Should build complete context for celery integration."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import build_context

        celery = real_repo.integrations.get('celery')
        context = build_context(celery)

        assert context.name == 'celery'
        assert len(context.metrics) > 0, "Celery should have metrics"
        assert 'celery' in context.metric_prefix.lower()

    def test_all_metrics_mode(self, real_repo):
        """all_metrics mode should set the flag in context."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import build_context

        redis = real_repo.integrations.get('redisdb')

        context_normal = build_context(redis, all_metrics=False)
        context_all = build_context(redis, all_metrics=True)

        assert context_normal.all_metrics_mode is False
        assert context_all.all_metrics_mode is True

    def test_to_prompt_context_generates_string(self, real_repo):
        """to_prompt_context should generate a non-empty string."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import build_context

        redis = real_repo.integrations.get('redisdb')
        context = build_context(redis)

        prompt = context.to_prompt_context()

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert 'redis' in prompt.lower()


class TestReadMetrics:
    """Tests for _read_metrics function."""

    def test_reads_metrics_from_metadata_csv(self, real_repo):
        """Should read metrics from metadata.csv."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_metrics

        redis = real_repo.integrations.get('redisdb')
        metrics = _read_metrics(redis)

        assert len(metrics) > 0, "Redis should have metrics in metadata.csv"
        assert all('metric_name' in m for m in metrics), "Each metric should have a metric_name"


class TestReadServiceChecks:
    """Tests for _read_service_checks function."""

    def test_reads_service_checks(self, real_repo):
        """Should read service checks from service_checks.json."""
        from ddev.cli.meta.scripts.dynamicd.context_builder import _read_service_checks

        redis = real_repo.integrations.get('redisdb')
        checks = _read_service_checks(redis)

        assert len(checks) > 0, "Redis should have service checks"
        assert all('name' in c for c in checks), "Each check should have a name"
