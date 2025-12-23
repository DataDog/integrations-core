# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

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
