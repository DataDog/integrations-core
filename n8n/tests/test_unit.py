# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest import mock

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.n8n import N8nCheck

from . import common


def test_unit_metrics(dd_run_check, instance, aggregator, mock_http_response):
    mock_http_response(file_path=common.get_fixture_path('n8n.txt'))
    check = N8nCheck('n8n', {}, [instance])
    dd_run_check(check)

    for metric in common.TEST_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_metrics_custom_prefx(dd_run_check, aggregator, mock_http_response):
    mock_http_response(file_path=common.get_fixture_path('n8n_custom.txt'))
    instance = {
        'openmetrics_endpoint': 'http://localhost:5678/metrics',
        'raw_metric_prefix': 'test_',
    }
    check = N8nCheck('n8n', {}, [instance])
    dd_run_check(check)

    for metric in common.TEST_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_version_metadata(datadog_agent, instance):
    # Mock the HTTP responses for version metadata collection only
    with mock.patch(
        'requests.Session.get',
        side_effect=[
            mock.Mock(ok=True, status_code=200, json=lambda: {'versionCli': '1.117.2'}),
        ],
    ):
        check = N8nCheck('n8n', {}, [instance])
        check.check_id = 'test:123'

        check._submit_version_metadata()

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '1',
        'version.minor': '117',
        'version.patch': '2',
        'version.raw': '1.117.2',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


def test_version_metadata_fallback(datadog_agent, instance):
    # Mock responses where version endpoint fails or returns malformed data
    with mock.patch(
        'requests.Session.get',
        side_effect=[
            # First call: version endpoint returns malformed version
            mock.Mock(ok=True, status_code=200, json=lambda: {'versionCli': 'invalid'}),
            # Second call: fallback to metrics for n8n version
            mock.Mock(ok=True, status_code=200, text=open(common.get_fixture_path('n8n.txt')).read()),
        ],
    ):
        check = N8nCheck('n8n', {}, [instance])
        check.check_id = 'test:456'

        # Call only the version metadata method
        check._submit_version_metadata()

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '1',
        'version.minor': '117',
        'version.patch': '2',
        'version.raw': '1.117.2',
    }
    datadog_agent.assert_metadata('test:456', version_metadata)
