# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.hdfs_namenode import HDFSNameNode

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    tags = ['namenode_url:{}'.format(instance["hdfs_namenode_jmx_uri"])]

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=tags)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('hdfs.namenode.jmx.can_connect', status=HDFSNameNode.OK, tags=tags)
