# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.hyperv import HypervCheck
from datadog_checks.hyperv.metrics import DEFAULT_COUNTERS


def test_check(aggregator, instance_refresh, dd_run_check):
    check = HypervCheck('hyperv', {}, [instance_refresh])
    dd_run_check(check)

    for counter_data in DEFAULT_COUNTERS:
        aggregator.assert_metric(counter_data[3])


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance_refresh):
    aggregator = dd_agent_check(instance_refresh)

    for counter_data in DEFAULT_COUNTERS:
        aggregator.assert_metric(counter_data[3])
