# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import iteritems

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
    for metric, value in iteritems(MAPREDUCE_JOB_METRIC_VALUES):
        aggregator.assert_metric(metric, value=value, tags=expected_tags, count=1)

    # Check the map task metrics
    for metric, value in iteritems(MAPREDUCE_MAP_TASK_METRIC_VALUES):
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_MAP_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the reduce task metrics
    for metric, value in iteritems(MAPREDUCE_REDUCE_TASK_METRIC_VALUES):
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_REDUCE_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the MapReduce job counter metrics
    for metric, attributes in iteritems(MAPREDUCE_JOB_COUNTER_METRIC_VALUES_READ):
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in iteritems(MAPREDUCE_JOB_COUNTER_METRIC_VALUES_WRITTEN):
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in iteritems(MAPREDUCE_JOB_COUNTER_METRIC_VALUES_RECORDS):
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


def test_auth(aggregator, dd_run_check, mocked_auth_request):
    """
    Test that we get all the metrics we're supposed to get
    """
    instance = MR_AUTH_CONFIG['instances'][0]

    # Instantiate the check
    mapreduce = MapReduceCheck('mapreduce', INIT_CONFIG, [instance])

    # Run the check once
    dd_run_check(mapreduce)

    # Check the service tests
    service_check_tags = ["url:{}".format(RM_URI)] + CUSTOM_TAGS
    aggregator.assert_service_check(
        MapReduceCheck.YARN_SERVICE_CHECK, status=MapReduceCheck.OK, tags=service_check_tags, count=1
    )
    aggregator.assert_service_check(
        MapReduceCheck.MAPREDUCE_SERVICE_CHECK, status=MapReduceCheck.OK, tags=service_check_tags, count=1
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
    for metric, value in iteritems(MAPREDUCE_JOB_METRIC_VALUES):
        aggregator.assert_metric(metric, value=value, tags=expected_tags, count=1)

    # Check the map task metrics
    for metric, value in iteritems(MAPREDUCE_MAP_TASK_METRIC_VALUES):
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_MAP_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the reduce task metrics
    for metric, value in iteritems(MAPREDUCE_REDUCE_TASK_METRIC_VALUES):
        aggregator.assert_metric(metric, value=value, tags=MAPREDUCE_REDUCE_TASK_METRIC_TAGS + expected_tags, count=1)

    # Check the MapReduce job counter metrics
    for metric, attributes in iteritems(MAPREDUCE_JOB_COUNTER_METRIC_VALUES_READ):
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in iteritems(MAPREDUCE_JOB_COUNTER_METRIC_VALUES_WRITTEN):
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )

    # Check the MapReduce job counter metrics
    for metric, attributes in iteritems(MAPREDUCE_JOB_COUNTER_METRIC_VALUES_RECORDS):
        aggregator.assert_metric(
            metric,
            value=attributes["value"],
            tags=attributes["tags"] + expected_tags,
            count=1,
        )
