# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import sys
import time
from distutils.version import LooseVersion  # pylint: disable=E0611,E0401
import pytest
import subprocess
import requests

# project
from datadog_checks.zk import ZookeeperCheck
import common


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def spin_up_zk():
    env = os.environ
    args = [
        'docker-compose', '-f', os.path.join(common.HERE, 'compose', 'zk.yaml')
    ]
    subprocess.check_call(args + ["up", "-d"], env=env)
    sys.stderr.write("Waiting for ZK to boot")
    for _ in xrange(2):
        try:
            res = requests.get(common.URL)
            res.raise_for_status()
        except Exception:
            time.sleep(1)
    yield
    subprocess.check_call(args + ["down"], env=env)


def test_check(aggregator, spin_up_zk):
    """
    Collect ZooKeeper metrics.
    """
    zk_check = ZookeeperCheck(common.CHECK_NAME, {}, {})
    zk_check.check(common.INSTANCE)
    zk_check.check(common.INSTANCE)

    # Test metrics
    for mname in common.STAT_METRICS:
        aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])

    zk_version = os.environ.get("ZK_VERSION") or "3.4.10"
    if zk_version and LooseVersion(zk_version) > LooseVersion("3.4.0"):
        for mname in common.MNTR_METRICS:
            aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])

    # Test service checks
    aggregator.assert_service_check("zookeeper.ruok", status=zk_check.OK)
    aggregator.assert_service_check("zookeeper.mode", status=zk_check.OK)

    expected_mode = common.INSTANCE['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1)
    aggregator.assert_all_metrics_covered()


def test_wrong_expected_mode(aggregator, spin_up_zk):
    """
    Raise a 'critical' service check when ZooKeeper is not in the expected mode.
    """
    zk_check = ZookeeperCheck(common.CHECK_NAME, {}, {})
    zk_check.check(common.WRONG_EXPECTED_MODE)

    # Test service checks
    aggregator.assert_service_check("zookeeper.mode", status=zk_check.CRITICAL)


def test_error_state(aggregator, spin_up_zk):
    """
    Raise a 'critical' service check when ZooKeeper is in an error state.
    Report status as down.
    """
    zk_check = ZookeeperCheck(common.CHECK_NAME, {}, {})
    with pytest.raises(Exception):
        zk_check.check(common.CONNECTION_FAILURE_CONFIG)

    aggregator.assert_service_check("zookeeper.ruok", status=zk_check.CRITICAL)

    aggregator.assert_metric("zookeeper.instances", tags=["mode:down"], count=1)

    expected_mode = common.CONNECTION_FAILURE_CONFIG['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1, count=1)
