# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW
from datadog_checks.dev.utils import get_metadata_metrics

from .common import GAUGES, MONOTONIC_COUNTS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in GAUGES:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)

    for metric in MONOTONIC_COUNTS:
        aggregator.assert_metric(metric, metric_type=aggregator.RATE)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=JVM_E2E_METRICS_NEW)

    aggregator.assert_service_check("ignite.can_connect")
