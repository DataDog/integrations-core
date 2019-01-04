# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.hyperv import HypervCheck
from datadog_checks.hyperv.metrics import DEFAULT_COUNTERS


def test_check(aggregator, instance):
    check = HypervCheck('hyperv', {}, {}, [instance])
    check.check(instance)

    for counter_data in DEFAULT_COUNTERS:
        aggregator.assert_metric(counter_data[3])
