# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for DynamicD context_builder functions.

These tests verify that dashboard parsing correctly extracts metrics, tags,
and tag values from real integration dashboards.
"""

import json
from unittest.mock import MagicMock

import anthropic
import httpx2
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


class TestGetApiKeys:
    """Tests for _get_api_keys helper."""

    def _make_app(self, anthropic_api_key: str, dd_api_key: str) -> MagicMock:
        app = MagicMock()
        app.config.ai.anthropic_api_key = anthropic_api_key
        app.config.org.config = {"api_key": dd_api_key}
        return app

    def test_returns_both_keys_when_configured(self):
        from ddev.cli.meta.scripts._dynamicd.cli import _get_api_keys

        app = self._make_app("sk-ant-test", "dd-key-123")
        llm_key, dd_key = _get_api_keys(app)

        assert llm_key == "sk-ant-test"
        assert dd_key == "dd-key-123"

    def test_aborts_when_llm_key_missing(self):
        from ddev.cli.meta.scripts._dynamicd.cli import _get_api_keys

        app = self._make_app("", "dd-key-123")
        _get_api_keys(app)

        app.abort.assert_called_once()

    def test_aborts_when_dd_key_missing(self):
        from ddev.cli.meta.scripts._dynamicd.cli import _get_api_keys

        app = self._make_app("sk-ant-test", "")
        _get_api_keys(app)

        app.abort.assert_called_once()


def _text_stream_response(text: str) -> httpx2.Response:
    events = [
        {
            'type': 'message_start',
            'message': {
                'id': 'msg_test',
                'type': 'message',
                'role': 'assistant',
                'model': 'claude-test',
                'content': [],
                'stop_reason': None,
                'stop_sequence': None,
                'usage': {'input_tokens': 1, 'output_tokens': 0},
            },
        },
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}},
        {'type': 'content_block_stop', 'index': 0},
        {
            'type': 'message_delta',
            'delta': {'stop_reason': 'end_turn', 'stop_sequence': None},
            'usage': {'output_tokens': 1},
        },
        {'type': 'message_stop'},
    ]
    body = ''.join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events)
    return httpx2.Response(200, headers={'content-type': 'text/event-stream'}, content=body.encode())


class TestGenerator:
    """Runs the generator through the installed SDK with the HTTP layer mocked.

    Mocking the client object instead would hide arguments the SDK rejects, such as the
    `temperature` argument that SDK 1.0.0 removed.
    """

    @pytest.fixture
    def requests(self, monkeypatch) -> list[dict]:
        sent: list[dict] = []

        def handler(request: httpx2.Request) -> httpx2.Response:
            sent.append(json.loads(request.content))
            return _text_stream_response('```python\nprint("simulating")\n```')

        real_client = anthropic.Anthropic

        def client_factory(api_key: str) -> anthropic.Anthropic:
            http_client = anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler))
            return real_client(api_key=api_key, http_client=http_client, max_retries=0)

        monkeypatch.setattr(anthropic, 'Anthropic', client_factory)
        return sent

    def test_generate_simulator_script(self, requests):
        from ddev.cli.meta.scripts._dynamicd.constants import DEFAULT_MODEL
        from ddev.cli.meta.scripts._dynamicd.generator import generate_simulator_script

        context = MagicMock(display_name='Redis')
        context.name = 'redisdb'
        context.to_prompt_context.return_value = 'redis context'

        script = generate_simulator_script(
            context=context,
            scenario='healthy',
            dd_site='datadoghq.com',
            metrics_per_batch=10,
            duration=60,
            api_key='test-key',
        )

        assert script == '#!/usr/bin/env python3\nprint("simulating")'
        assert [request['model'] for request in requests] == [DEFAULT_MODEL, DEFAULT_MODEL]

    def test_fix_script_error(self, requests):
        from ddev.cli.meta.scripts._dynamicd.generator import fix_script_error

        script = fix_script_error(
            original_script='print(',
            error_message='SyntaxError',
            attempt=1,
            api_key='test-key',
        )

        assert script == '#!/usr/bin/env python3\nprint("simulating")'
        assert len(requests) == 1


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
