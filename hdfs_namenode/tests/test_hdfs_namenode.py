# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from six import iteritems

from datadog_checks.hdfs_namenode import HDFSNameNode

from .common import (
    CUSTOM_TAGS,
    HDFS_NAMENODE_AUTH_CONFIG,
    HDFS_NAMENODE_CONFIG,
    HDFS_NAMESYSTEM_METRIC_TAGS,
    HDFS_NAMESYSTEM_METRICS_VALUES,
    HDFS_NAMESYSTEM_MUTUAL_METRICS_VALUES,
    HDFS_NAMESYSTEM_STATE_METRICS_VALUES,
    HDFS_RAW_VERSION,
)

pytestmark = pytest.mark.unit

CHECK_ID = 'test:123'


def test_check(aggregator, mocked_request):
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # Run the check once
    hdfs_namenode.check(instance)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.OK, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1
    )

    for metric, value in iteritems(HDFS_NAMESYSTEM_STATE_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1)

    for metric, value in iteritems(HDFS_NAMESYSTEM_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1)

    for metric, value in iteritems(HDFS_NAMESYSTEM_MUTUAL_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=2)

    aggregator.assert_all_metrics_covered()


def test_metadata(aggregator, mocked_request, datadog_agent):
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # Run the check once
    hdfs_namenode.check_id = CHECK_ID
    hdfs_namenode.check(instance)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.OK, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1
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
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # Run the check once
    hdfs_namenode.check(instance)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.OK, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1
    )
