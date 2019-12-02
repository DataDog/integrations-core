# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import iteritems

from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import (
    CUSTOM_TAGS,
    HDFS_DATANODE_AUTH_CONFIG,
    HDFS_DATANODE_CONFIG,
    HDFS_DATANODE_METRIC_TAGS,
    HDFS_DATANODE_METRICS_VALUES,
    HDFS_RAW_VERSION,
)

pytestmark = pytest.mark.unit

CHECK_ID = 'test:123'


def test_check(aggregator, mocked_request):
    """
    Test that we get all the metrics we're supposed to get
    """

    instance = HDFS_DATANODE_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    # Run the check once
    hdfs_datanode.check(instance)

    # Make sure the service is up
    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.OK, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1
    )

    for metric, value in iteritems(HDFS_DATANODE_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1)

    aggregator.assert_all_metrics_covered()


def test_metadata(aggregator, mocked_request, mocked_metadata_request, datadog_agent):
    """
    Test that we get the metadata we are expecting
    """

    instance = HDFS_DATANODE_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    # Run the check once
    hdfs_datanode.check_id = CHECK_ID
    hdfs_datanode.check(instance)

    # Make sure the service is up
    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.OK, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1
    )

    major, minor, patch = HDFS_RAW_VERSION.split('.')

    version_metadata = {
        'version.raw': HDFS_RAW_VERSION,
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }

    datadog_agent.assert_metadata(CHECK_ID, version_metadata)
    datadog_agent.assert_metadata_count(5)


def test_auth(aggregator, mocked_auth_request):
    """
    Test that we can connect to the endpoint when we authenticate
    """
    instance = HDFS_DATANODE_AUTH_CONFIG['instances'][0]
    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, [instance])

    # Run the check once
    hdfs_datanode.check(instance)

    # Make sure the service is up
    aggregator.assert_service_check(
        HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.OK, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1
    )
