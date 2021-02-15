# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common


@pytest.mark.e2e
def test_openstack_controller_e2e(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in common.DEFAULT_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
