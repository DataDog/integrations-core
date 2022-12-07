# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.hdfs_datanode import HDFSDataNode

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    # We do not do aggregator.assert_all_metrics_covered() because depending on timing, some other metrics may appear
    aggregator = dd_agent_check(instance, rate=True)

    tags = ['datanode_url:{}'.format(instance["hdfs_datanode_jmx_uri"])]

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=tags)

    aggregator.assert_service_check('hdfs.datanode.jmx.can_connect', status=HDFSDataNode.OK, tags=tags)
