# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import platform

import pytest

from datadog_checks.scylla import ScyllaCheck

from .common import FLAKY_METRICS, INSTANCE_DEFAULT_METRICS_V2


@pytest.mark.skipif(platform.python_version() < "3", reason='OpenMetrics V2 is only available with Python 3')
def test_check_ok_omv2(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for metric in INSTANCE_DEFAULT_METRICS_V2:
        if metric in FLAKY_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', ScyllaCheck.OK)
