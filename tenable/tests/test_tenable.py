# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.tenable import TenableCheck


def test_check(aggregator, instance):
    check = TenableCheck('tenable', {}, {})
    check.check(instance)

    aggregator.assert_all_metrics_covered()
