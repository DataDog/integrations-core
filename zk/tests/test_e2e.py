# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from distutils.version import LooseVersion  # pylint: disable=E0611,E0401

import pytest

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check, get_instance):
    aggregator = dd_agent_check(get_instance, rate=True)

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
