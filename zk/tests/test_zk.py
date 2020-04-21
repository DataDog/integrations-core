# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
from distutils.version import LooseVersion  # pylint: disable=E0611,E0401

import mock
import pytest

from datadog_checks.zk import ZookeeperCheck

from . import common, conftest

pytestmark = pytest.mark.integration


def test_check(aggregator, dd_environment, get_instance):
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
    if zk_version and LooseVersion(zk_version) < LooseVersion("3.5.0"):
        for mname in common.MNTR_METRICS:
            aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])
    if zk_version and LooseVersion(zk_version) < LooseVersion("3.6.0"):
        for mname in common.METRICS_34:
            aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])
    if zk_version and LooseVersion(zk_version) >= LooseVersion("3.6.0"):
        for mname in common.METRICS_36:
            aggregator.assert_metric(mname)

    common.assert_service_checks_ok(aggregator)

    expected_mode = get_instance['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1)
    aggregator.assert_all_metrics_covered()


def test_wrong_expected_mode(aggregator, dd_environment, get_invalid_mode_instance):
    """
    Raise a 'critical' service check when ZooKeeper is not in the expected mode.
    """
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, {})
    zk_check.check(get_invalid_mode_instance)

    # Test service checks
    aggregator.assert_service_check("zookeeper.mode", status=zk_check.CRITICAL)


def test_error_state(aggregator, dd_environment, get_conn_failure_config):
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


@pytest.mark.usefixtures('dd_environment')
def test_metadata(datadog_agent):
    check = ZookeeperCheck(conftest.CHECK_NAME, {}, [conftest.VALID_CONFIG])

    check.check_id = 'test:123'

    check.check(conftest.VALID_CONFIG)

    raw_version = common.ZK_VERSION
    major, minor = raw_version.split('.')[:2]
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': mock.ANY,
        'version.raw': mock.ANY,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
