# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in common.EXPECTED_METRICS:
        for device in common.EXPECTED_DEVICE:
            aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, device=device)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
