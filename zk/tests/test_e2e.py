# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


@pytest.mark.e2e
def test_e2e(dd_agent_check, get_instance):
    aggregator = dd_agent_check(get_instance, rate=True)

    common.assert_stat_metrics(aggregator)
    common.assert_mntr_metrics_by_version(aggregator)
    common.assert_service_checks_ok(aggregator)

    expected_mode = get_instance['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1)
    aggregator.assert_all_metrics_covered()
