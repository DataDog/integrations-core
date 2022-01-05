# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py2, requires_py3
from datadog_checks.hyperv import HypervCheck
from datadog_checks.hyperv.metrics import DEFAULT_COUNTERS


@requires_py3
def test_check(aggregator, dd_default_hostname, dd_run_check):
    check = HypervCheck('hyperv', {}, [{}])
    check.hostname = dd_default_hostname

    # Run twice for counters that require 2 data points
    dd_run_check(check)
    dd_run_check(check)

    aggregator.assert_service_check(
        'hyperv.windows.perf.health', ServiceCheck.OK, count=2, tags=['server:{}'.format(dd_default_hostname)]
    )
    _assert_metrics(aggregator)


@requires_py2
def test_check_legacy(aggregator, instance_refresh, dd_run_check):
    check = HypervCheck('hyperv', {}, [instance_refresh])
    dd_run_check(check)

    _assert_metrics(aggregator)


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance_refresh):
    aggregator = dd_agent_check(instance_refresh)

    _assert_metrics(aggregator)


def _assert_metrics(aggregator):
    for counter_data in DEFAULT_COUNTERS:
        aggregator.assert_metric(counter_data[3])

    aggregator.assert_all_metrics_covered()
