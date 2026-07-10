# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
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


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)

    # discovery can't predict the discovered namenode_url tag, and Autodiscovery adds its own
    # container tags (docker_image, image_id, ...) that a static instance never carries, so tags
    # aren't asserted here.
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('hdfs.namenode.jmx.can_connect', status=HDFSNameNode.OK)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, HDFSNameNode, compose_service='namenode')
