# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import (
    CUSTOM_TAGS, HDFS_DATANODE_CONFIG, HDFS_DATANODE_AUTH_CONFIG, HDFS_DATANODE_METRICS_VALUES,
    HDFS_DATANODE_METRIC_TAGS
)


def test_check(aggregator, mocked_request):
    """
    Test that we get all the metrics we're supposed to get
    """

    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, {})

    # Run the check once
    hdfs_datanode.check(HDFS_DATANODE_CONFIG['instances'][0])

    # Make sure the service is up
    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.OK, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1
    )

    for metric, value in HDFS_DATANODE_METRICS_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1)

    aggregator.assert_all_metrics_covered()


def test_auth(aggregator, mocked_auth_request):
    """
    Test that we can connect to the endpoint when we authenticate
    """

    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, {})

    # Run the check once
    hdfs_datanode.check(HDFS_DATANODE_AUTH_CONFIG['instances'][0])

    # Make sure the service is up
    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.OK, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1
    )
