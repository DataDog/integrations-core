# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    at_least = 0 if device == '/dev/sdb1' else 1
    for metric in common.EXPECTED_METRICS:
        for device in common.EXPECTED_DEVICES:
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, device=device, at_least=at_least)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
