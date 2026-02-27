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


def test_readiness_check_ready(aggregator, instance):
    with mock.patch(
        'requests.Session.get',
        return_value=mock.Mock(ok=True, status_code=200),
    ):
        check = N8nCheck('n8n', {}, [instance])
        check._check_n8n_readiness()

    # Assert metric value is 1 (ready) with status_code:200 tag
    aggregator.assert_metric('n8n.readiness.check', value=1, tags=['status_code:200'])


def test_readiness_check_not_ready(aggregator, instance):
    with mock.patch(
        'requests.Session.get',
        return_value=mock.Mock(ok=False, status_code=503),
    ):
        check = N8nCheck('n8n', {}, [instance])
        check._check_n8n_readiness()

    # Assert metric value is 0 (not ready) with status_code:503 tag
    aggregator.assert_metric('n8n.readiness.check', value=0, tags=['status_code:503'])


def test_readiness_check_no_status_code(aggregator, instance):
    with mock.patch(
        'requests.Session.get',
        return_value=mock.Mock(ok=False, status_code=None),
    ):
        check = N8nCheck('n8n', {}, [instance])
        check._check_n8n_readiness()

    # Assert metric value is 0 (not ready) with status_code:null tag
    aggregator.assert_metric('n8n.readiness.check', value=0, tags=['status_code:null'])
