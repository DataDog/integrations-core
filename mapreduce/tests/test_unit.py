# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import (
    HTTPClientConnectionError,
    HTTPClientConnectTimeoutError,
    HTTPClientInvalidURLError,
    HTTPClientReadTimeoutError,
    HTTPClientSSLError,
)
from datadog_checks.mapreduce import MapReduceCheck

from .common import (
    CLUSTER_TAGS,
    COMMON_TAGS,
    CUSTOM_TAGS,
    INIT_CONFIG,
    MAPREDUCE_CLUSTER_TAG,
    MAPREDUCE_JOB_COUNTER_METRIC_VALUES_READ,
    MAPREDUCE_JOB_COUNTER_METRIC_VALUES_RECORDS,
    MAPREDUCE_JOB_COUNTER_METRIC_VALUES_WRITTEN,
    MAPREDUCE_JOB_METRIC_VALUES,
    MAPREDUCE_MAP_TASK_METRIC_TAGS,
    MAPREDUCE_MAP_TASK_METRIC_VALUES,
    MAPREDUCE_REDUCE_TASK_METRIC_TAGS,
    MAPREDUCE_REDUCE_TASK_METRIC_VALUES,
    MR_AUTH_CONFIG,
    MR_CONFIG,
    RM_URI,
    TEST_PASSWORD,
    TEST_USERNAME,
    YARN_APPS_URL,
)


def test_check(aggregator, dd_run_check, mocked_request):
    """
    Test that we get all the metrics we're supposed to get
    """
    instance = MR_CONFIG['instances'][0]

    # Instantiate the check
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [instance])

    # Run the check once
    dd_run_check(mapreduce)

    # expected tags contains both mapreduce_cluster and cluster_name tags
    expected_tags = COMMON_TAGS + CLUSTER_TAGS

    # Check the MapReduce job metrics
    for metric, value in MAPREDUCE_JOB_METRIC_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=expected_tags, count=1)

    # Check the map task metrics
    for metric, value in MAPREDUCE_MAP_TASK_METRIC_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_MAP_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the reduce task metrics
    for metric, value in MAPREDUCE_REDUCE_TASK_METRIC_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_REDUCE_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the MapReduce job counter metrics
    for metric, attributes in MAPREDUCE_JOB_COUNTER_METRIC_VALUES_READ.items():
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in MAPREDUCE_JOB_COUNTER_METRIC_VALUES_WRITTEN.items():
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in MAPREDUCE_JOB_COUNTER_METRIC_VALUES_RECORDS.items():
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the service tests
    service_check_tags = ["url:{}".format(RM_URI)] + CUSTOM_TAGS
    aggregator.assert_service_check(
        MapReduceCheck.YARN_SERVICE_CHECK, status=MapReduceCheck.OK, tags=service_check_tags, count=1
    )
    aggregator.assert_service_check(
        MapReduceCheck.MAPREDUCE_SERVICE_CHECK, status=MapReduceCheck.OK, tags=service_check_tags, count=1
    )

    aggregator.assert_all_metrics_covered()


def test_auth():
    """
    Test that the configured credentials are sent with every request
    """
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [MR_AUTH_CONFIG['instances'][0]])

    assert mapreduce.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)


@pytest.mark.parametrize(
    'outcome, message_prefix',
    [
        pytest.param(HTTPClientReadTimeoutError('read timed out'), 'Request timeout', id='read timeout'),
        pytest.param(HTTPClientConnectTimeoutError('connect timed out'), 'Request timeout', id='connect timeout'),
        pytest.param(HTTPClientConnectionError('connection refused'), 'Request failed', id='connection error'),
        pytest.param(HTTPClientSSLError('certificate verify failed'), 'Request failed', id='ssl error'),
        pytest.param(HTTPClientInvalidURLError('invalid url'), 'Request failed', id='invalid url'),
        pytest.param(FakeHTTPResponse(status_code=500), 'Request failed', id='error status'),
        pytest.param(
            FakeHTTPResponse(json_error=json.JSONDecodeError('Expecting value', '', 0)),
            'JSON Parse failed',
            id='invalid json',
        ),
    ],
)
def test_request_failure_reports_critical(aggregator, fake_http, outcome, message_prefix):
    instance = MR_CONFIG['instances'][0]
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [instance])
    fake_http.register_response('GET', YARN_APPS_URL, outcome)

    with pytest.raises(Exception) as excinfo:
        mapreduce.check(instance)

    aggregator.assert_service_check(
        MapReduceCheck.YARN_SERVICE_CHECK,
        status=MapReduceCheck.CRITICAL,
        tags=['url:{}'.format(RM_URI)],
        # The stub matches messages as regular expressions, and the URL contains `?`.
        message=re.escape('{}: {}, {}'.format(message_prefix, YARN_APPS_URL, excinfo.value)),
        count=1,
    )


def test_disable_legacy_cluster_tag(aggregator, dd_run_check, mocked_request):
    """
    Test that we get all the metrics we're supposed to get
    """
    instance = MR_CONFIG['instances'][0]
    instance['disable_legacy_cluster_tag'] = True

    # Instantiate the check
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [instance])

    # Run the check once
    dd_run_check(mapreduce)

    # Only mapreduce_cluster tag
    expected_tags = COMMON_TAGS
    expected_tags.append(MAPREDUCE_CLUSTER_TAG)

    # Check the MapReduce job metrics
    for metric, value in MAPREDUCE_JOB_METRIC_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=expected_tags, count=1)

    # Check the map task metrics
    for metric, value in MAPREDUCE_MAP_TASK_METRIC_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_MAP_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the reduce task metrics
    for metric, value in MAPREDUCE_REDUCE_TASK_METRIC_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_REDUCE_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the MapReduce job counter metrics
    for metric, attributes in MAPREDUCE_JOB_COUNTER_METRIC_VALUES_READ.items():
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in MAPREDUCE_JOB_COUNTER_METRIC_VALUES_WRITTEN.items():
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in MAPREDUCE_JOB_COUNTER_METRIC_VALUES_RECORDS.items():
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )
