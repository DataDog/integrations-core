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
)

pytestmark = pytest.mark.unit


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


def test_auth(aggregator, mocked_auth_request):
    instance = HDFS_NAMENODE_AUTH_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])

    # Run the check once
    hdfs_namenode.check(instance)

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.OK, tags=HDFS_NAMESYSTEM_METRIC_TAGS + CUSTOM_TAGS, count=1
    )
