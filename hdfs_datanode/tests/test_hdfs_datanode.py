# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import HDFS_DATANODE_CONFIG, HDFS_DATANODE_METRICS_VALUES, HDFS_DATANODE_METRIC_TAGS


def test_check(aggregator):
    """
    Test that we get all the metrics we're supposed to get
    """

    hdfs_datanode = HDFSDataNode('hdfs_datanode', {}, {})

    hdfs_datanode.check(HDFS_DATANODE_CONFIG['instances'][0])

    for metric, value in HDFS_DATANODE_METRICS_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=HDFS_DATANODE_METRIC_TAGS, count=1)

    aggregator.assert_all_metrics_covered()
