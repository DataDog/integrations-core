# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse, RecordedRequest
from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
from datadog_checks.openmetrics import OpenMetricsCheck

from .common import CHECK_NAME

instance_new = {
    'openmetrics_endpoint': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1', 'counter2'],
    'collect_histogram_buckets': True,
}

instance_new_strict = {
    'openmetrics_endpoint': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1'],
    'collect_histogram_buckets': True,
    'use_latest_spec': True,
}

instance_unavailable = {
    'openmetrics_endpoint': 'http://127.0.0.1:4243/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1'],
    'ignore_connection_errors': True,
}


@pytest.mark.parametrize('poll_mock_fixture', ['prometheus_poll_mock', 'openmetrics_poll_mock'])
def test_openmetrics(aggregator, dd_run_check, request, poll_mock_fixture):
    request.getfixturevalue(poll_mock_fixture)

    check = OpenMetricsCheck('openmetrics', {}, [instance_new])
    dd_run_check(check)

    aggregator.assert_metric(
        '{}.renamed.metric1'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.metric2'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.counter1.count'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host2'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_metric(
        '{}.counter2.count'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host2'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_all_metrics_covered()

    scraper = check.scrapers[instance_new['openmetrics_endpoint']]
    assert check.http.get_header('Accept') is None
    assert scraper.http.get_header('Accept') == 'text/plain'
    assert scraper.http is not check.http


def test_openmetrics_use_latest_spec(aggregator, dd_run_check, fake_http, openmetrics_payload, caplog):
    # We want to make sure that when `use_latest_spec` is enabled, we use the OpenMetrics parser
    # even when the response's `Content-Type` doesn't declare the appropriate media type.
    content = openmetrics_payload.encode('utf-8')
    fake_http.register_response(
        'GET',
        instance_new_strict['openmetrics_endpoint'],
        FakeHTTPResponse(
            content=content,
            text=openmetrics_payload,
            headers={'Content-Type': 'text/plain'},
            content_chunks=(content,),
            lines=openmetrics_payload.splitlines(),
        ),
        match_options={'stream': True},
    )

    check = OpenMetricsCheck('openmetrics', {}, [instance_new_strict])
    dd_run_check(check)

    aggregator.assert_metric(
        '{}.renamed.metric1'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host1', 'flavor:test', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.metric2'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'timestamp:123', 'node:host2', 'matched_label:foobar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        '{}.counter1.count'.format(CHECK_NAME),
        tags=['endpoint:http://localhost:10249/metrics', 'node:host2'],
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_all_metrics_covered()

    scraper = check.scrapers[instance_new_strict['openmetrics_endpoint']]
    assert check.http.get_header('Accept') is None
    assert caplog.text == ''
    assert scraper.http.get_header('accept') == (
        'application/openmetrics-text;version=1.0.0,application/openmetrics-text;version=0.0.1'
    )
    assert scraper.http is not check.http
    fake_http.assert_requests([RecordedRequest('GET', instance_new_strict['openmetrics_endpoint'], {'stream': True})])
    fake_http.assert_all_responses_consumed()


def test_openmetrics_empty_response(aggregator, dd_run_check, fake_http):
    fake_http.register_response(
        'GET',
        instance_new['openmetrics_endpoint'],
        FakeHTTPResponse(content=b'', lines=()),
        match_options={'stream': True},
    )

    check = OpenMetricsCheck('openmetrics', {}, [instance_new])
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    fake_http.assert_requests([RecordedRequest('GET', instance_new['openmetrics_endpoint'], {'stream': True})])
    fake_http.assert_all_responses_consumed()


def test_openmetrics_endpoint_unavailable(aggregator, dd_run_check, fake_http):
    fake_http.register_response(
        'GET',
        instance_unavailable['openmetrics_endpoint'],
        HTTPClientConnectionError('Connection refused'),
        match_options={'stream': True},
    )
    check = OpenMetricsCheck('openmetrics', {}, [instance_unavailable])
    dd_run_check(check)

    # Collects no metrics without error.
    aggregator.assert_all_metrics_covered()
    fake_http.assert_requests([RecordedRequest('GET', instance_unavailable['openmetrics_endpoint'], {'stream': True})])
    fake_http.assert_all_responses_consumed()
