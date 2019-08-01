# (C) Datadog, Inc. 2010-2019
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
    metrics_to_check = []
    if zk_version and LooseVersion(zk_version) >= LooseVersion("3.4.0"):
        metrics_to_check = common.MNTR_METRICS
    if zk_version and LooseVersion(zk_version) <= LooseVersion("3.5.0"):
        metrics_to_check.extend(common.METRICS_34)
    for mname in metrics_to_check:
        aggregator.assert_metric(mname, tags=["mode:standalone", "mytag"])

    common.assert_service_checks_ok(aggregator)

    expected_mode = get_instance['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1)
    aggregator.assert_all_metrics_covered()
