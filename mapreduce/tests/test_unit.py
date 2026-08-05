# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPRequestError
from datadog_checks.dev.http import MockHTTPResponse
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


def test_json_parse_failure_keeps_url_in_service_check(aggregator, dd_run_check, mock_http):
    """The URL is the only per-endpoint discriminator, so a non-JSON body must still name it."""
    mock_http.get.side_effect = lambda url, *args, **kwargs: MockHTTPResponse(content='<html>not json</html>')
    instance = MR_CONFIG['instances'][0]
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [instance])

    # `dd_run_check` re-raises the check's traceback as a plain Exception.
    with pytest.raises(Exception, match='JSONDecodeError'):
        dd_run_check(mapreduce)

    message = aggregator.service_checks(MapReduceCheck.YARN_SERVICE_CHECK)[0].message
    assert message.startswith('JSON Parse failed: {}'.format(RM_URI))


def test_auth():
    instance = MR_AUTH_CONFIG['instances'][0]
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [instance])

    assert mapreduce.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)


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


def test_malformed_header_still_reports_critical(aggregator, dd_run_check, mock_http):
    """A server-sent malformed header must still emit mapreduce.resource_manager.can_connect.

    urllib3 raises InvalidHeader for a multi-valued Content-Length and requests re-raises it as
    its own InvalidHeader, which subclasses ValueError. The agnostic translator has no equivalent
    subtype and collapses it into a bare HTTPRequestError, so the last arm has to name that type.
    """
    message = 'Content-Length contained multiple unmatching values'
    mock_http.get.side_effect = HTTPRequestError(message)
    instance = MR_CONFIG['instances'][0]
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [instance])

    with pytest.raises(Exception, match=message):
        dd_run_check(mapreduce)

    aggregator.assert_service_check(MapReduceCheck.YARN_SERVICE_CHECK, status=MapReduceCheck.CRITICAL, count=1)
    # Merge base reported the bare error text here, not the "Request failed" prefix that the
    # status/connection arm uses. Pin it so the fix stays on the last arm.
    assert aggregator.service_checks(MapReduceCheck.YARN_SERVICE_CHECK)[0].message == message
