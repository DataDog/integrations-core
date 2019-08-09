# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import sys

import pytest

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric['metric'], metric_type=aggregator.GAUGE, device=metric['device'])
    if sys.platform == 'darwin':
        for metric in common.OSX_METRICS:
            aggregator.assert_metric(metric['metric'], metric_type=aggregator.GAUGE, device=metric['device'])
    aggregator.assert_all_metrics_covered()
