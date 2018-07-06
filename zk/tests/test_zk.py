# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
from distutils.version import LooseVersion  # pylint: disable=E0611,E0401
import pytest

# project
from datadog_checks.zk import ZookeeperCheck
import conftest


def test_check(aggregator, spin_up_zk, get_instance):
    """
    Collect ZooKeeper metrics.
    """
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, {})
    zk_check.check(get_instance)
    zk_check.check(get_instance)

    # Test metrics
    for mname in conftest.STAT_METRICS:
        aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])

    zk_version = os.environ.get("ZK_VERSION") or "3.4.10"
    if zk_version and LooseVersion(zk_version) > LooseVersion("3.4.0"):
        for mname in conftest.MNTR_METRICS:
            aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])

    # Test service checks
    aggregator.assert_service_check("zookeeper.ruok", status=zk_check.OK)
    aggregator.assert_service_check("zookeeper.mode", status=zk_check.OK)

    expected_mode = get_instance['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1)
    aggregator.assert_all_metrics_covered()


def test_wrong_expected_mode(aggregator, spin_up_zk, get_invalid_mode_instance):
    """
    Raise a 'critical' service check when ZooKeeper is not in the expected mode.
    """
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, {})
    zk_check.check(get_invalid_mode_instance)

    # Test service checks
    aggregator.assert_service_check("zookeeper.mode", status=zk_check.CRITICAL)


def test_error_state(aggregator, spin_up_zk, get_conn_failure_config):
    """
    Raise a 'critical' service check when ZooKeeper is in an error state.
    Report status as down.
    """
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, {})
    with pytest.raises(Exception):
        zk_check.check(get_conn_failure_config)

    aggregator.assert_service_check("zookeeper.ruok", status=zk_check.CRITICAL)

    aggregator.assert_metric("zookeeper.instances", tags=["mode:down"], count=1)

    expected_mode = get_conn_failure_config['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1, count=1)
