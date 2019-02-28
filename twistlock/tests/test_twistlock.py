# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.twistlock import TwistlockCheck


def test_check(aggregator, instance):
    check = TwistlockCheck('twistlock', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
